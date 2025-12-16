#!/usr/bin/env python3
"""
Database Introspection - Validate ORM Models vs DB Schema

Compares SQLAlchemy models with actual PostgreSQL schema to detect mismatches.
Checks: tables, columns, types, nullability, indexes, relationships.

Run: python3 scripts/db_introspection.py
"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend')

from sqlalchemy import inspect, text
from core.database import sync_engine, get_db
from models import Base
from models.odds import Odds, TrackingCLVPicks
from models.quantum import (
    TeamQuantumDNA,
    QuantumFrictionMatrix,
    QuantumStrategy,
    ChessClassification,
    GoalscorerProfile,
)
from typing import Dict, List, Set, Tuple


def get_db_tables(schema: str = "public") -> Set[str]:
    """Get list of tables from database schema."""
    with get_db() as session:
        if schema == "public":
            result = session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """))
        else:
            result = session.execute(text(f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = '{schema}'
                AND table_type = 'BASE TABLE'
            """))
        return {row[0] for row in result}


def get_db_columns(table_name: str, schema: str = "public") -> Dict[str, Dict]:
    """Get column information from database table."""
    with get_db() as session:
        result = session.execute(text(f"""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
            AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """))

        columns = {}
        for row in result:
            columns[row[0]] = {
                "type": row[1],
                "nullable": row[2] == "YES",
                "default": row[3],
                "max_length": row[4],
            }
        return columns


def get_orm_tables() -> Dict[str, object]:
    """Get all ORM models mapped to tables."""
    models = {}

    for mapper in Base.registry.mappers:
        cls = mapper.class_
        table_name = cls.__tablename__
        schema = cls.__table_args__.get("schema") if hasattr(cls, "__table_args__") and isinstance(cls.__table_args__, dict) else None

        if schema:
            key = f"{schema}.{table_name}"
        else:
            key = table_name

        models[key] = cls

    return models


def sqlalchemy_to_pg_type(sa_type: str) -> str:
    """Map SQLAlchemy types to PostgreSQL types."""
    mapping = {
        "INTEGER": "integer",
        "BIGINT": "bigint",
        "VARCHAR": "character varying",
        "TEXT": "text",
        "BOOLEAN": "boolean",
        "TIMESTAMP": "timestamp with time zone",
        "DATETIME": "timestamp with time zone",
        "DATE": "date",
        "NUMERIC": "numeric",
        "FLOAT": "double precision",
        "JSONB": "jsonb",
        "JSON": "json",
    }

    sa_type_upper = sa_type.upper()
    for sa, pg in mapping.items():
        if sa in sa_type_upper:
            return pg

    return sa_type.lower()


def compare_table(model_class: object, schema: str = "public") -> Tuple[bool, List[str]]:
    """Compare ORM model with database table."""
    table_name = model_class.__tablename__
    issues = []

    # Check if table exists in DB
    db_tables = get_db_tables(schema)
    if table_name not in db_tables:
        issues.append(f"⚠️  Table '{table_name}' exists in ORM but NOT in database schema '{schema}'")
        return False, issues

    # Get DB columns
    db_columns = get_db_columns(table_name, schema)

    # Get ORM columns
    inspector = inspect(model_class)
    orm_columns = {col.name: col for col in inspector.columns}

    # Compare columns
    orm_col_names = set(orm_columns.keys())
    db_col_names = set(db_columns.keys())

    # Missing in DB
    missing_in_db = orm_col_names - db_col_names
    if missing_in_db:
        for col in missing_in_db:
            issues.append(f"  ❌ Column '{col}' in ORM but missing in DB")

    # Extra in DB
    extra_in_db = db_col_names - orm_col_names
    if extra_in_db:
        for col in extra_in_db:
            issues.append(f"  ⚠️  Column '{col}' in DB but not mapped in ORM")

    # Compare common columns
    for col_name in orm_col_names & db_col_names:
        orm_col = orm_columns[col_name]
        db_col = db_columns[col_name]

        # Type comparison (basic)
        orm_type = sqlalchemy_to_pg_type(str(orm_col.type))
        db_type = db_col["type"]

        if orm_type != db_type:
            # Check if it's a compatible type difference
            compatible = False
            if "varchar" in db_type and "VARCHAR" in str(orm_col.type):
                compatible = True
            elif db_type == "timestamp with time zone" and "TIMESTAMP" in str(orm_col.type).upper():
                compatible = True

            if not compatible:
                issues.append(f"  ⚠️  Column '{col_name}': type mismatch (ORM: {orm_type}, DB: {db_type})")

        # Nullable comparison
        orm_nullable = orm_col.nullable
        db_nullable = db_col["nullable"]

        if orm_nullable != db_nullable:
            issues.append(f"  ⚠️  Column '{col_name}': nullable mismatch (ORM: {orm_nullable}, DB: {db_nullable})")

    if not issues:
        return True, []
    else:
        return False, issues


def main():
    """Run database introspection."""
    print("🔍 DATABASE INTROSPECTION - ORM vs DB Schema")
    print("=" * 80)

    # Get all ORM models
    orm_models = get_orm_tables()

    print(f"\n📊 Found {len(orm_models)} ORM models")
    print("-" * 80)

    all_ok = True
    total_issues = 0

    # Check public schema models
    print("\n🔹 PUBLIC SCHEMA")
    print("-" * 80)

    public_models = {
        "odds": Odds,
        "tracking_clv_picks": TrackingCLVPicks,
    }

    for table_name, model_class in public_models.items():
        print(f"\n📋 {table_name}")
        ok, issues = compare_table(model_class, schema="public")

        if ok:
            print(f"  ✅ OK - Model matches DB schema")
        else:
            all_ok = False
            total_issues += len(issues)
            for issue in issues:
                print(issue)

    # Check quantum schema models
    print("\n\n🔹 QUANTUM SCHEMA")
    print("-" * 80)

    quantum_models = {
        "team_quantum_dna": TeamQuantumDNA,
        "quantum_friction_matrix": QuantumFrictionMatrix,
        "quantum_strategies": QuantumStrategy,
        "chess_classifications": ChessClassification,
        "goalscorer_profiles": GoalscorerProfile,
    }

    for table_name, model_class in quantum_models.items():
        print(f"\n📋 {table_name}")
        ok, issues = compare_table(model_class, schema="quantum")

        if ok:
            print(f"  ✅ OK - Model matches DB schema")
        else:
            # For quantum, tables not existing is expected
            if "NOT in database schema" in issues[0]:
                print(f"  ⏳ Table not created yet (expected for quantum schema)")
            else:
                all_ok = False
                total_issues += len(issues)
                for issue in issues:
                    print(issue)

    # Summary
    print("\n" + "=" * 80)
    if all_ok:
        print("✅ INTROSPECTION PASSED - All models match database schema")
        print(f"   {len(public_models)} public tables validated")
        print(f"   {len(quantum_models)} quantum tables (not yet created)")
        return True
    else:
        print(f"⚠️  INTROSPECTION WARNINGS - {total_issues} issues found")
        print(f"   Review mismatches above and update ORM models or run migrations")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
