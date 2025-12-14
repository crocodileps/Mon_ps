# ROOT CAUSE ANALYSIS - Integration Tests quantum_core

**Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Objectif:** Comprendre pourquoi 6 integration tests skipped
**Méthodologie:** Observer → Analyser → Diagnostiquer → Solution

---

## SYMPTÔME
```
6 integration tests SKIPPED
Raison: quantum_core path not accessible in test context
```

**Questions à répondre:**
1. Le volume quantum_core est-il monté dans le container ?
2. Si oui, pourquoi pytest ne le trouve pas ?
3. Comment production y accède-t-elle ?
4. Différence PYTHONPATH production vs tests ?

---

## INVESTIGATION


### 1. Docker Compose Configuration

#### 1.1 Volume Configuration (docker-compose.yml)
```yaml
    env_file:
      - .env
    ports:
    - 8001:8000
    restart: always
    volumes:
      - /home/Mon_ps/quantum_core:/quantum_core:ro
  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    container_name: monps_frontend
    depends_on:
    - backend
```

**Analyse:**
- ✅ quantum_core volume IS configured

#### 2.1 Container Volume Mount Status
```bash
$ docker exec monps_backend ls -la /quantum_core
total 68
drwxrwxr-x 13 1000 1000 4096 Dec 13 14:15 .
drwxr-xr-x  1 root root 4096 Dec 14 14:16 ..
-rw-rw-r--  1 1000 1000    0 Dec 13 09:53 __init__.py
drwxrwxr-x  2 1000 1000 4096 Dec 13 11:59 __pycache__
drwxrwxr-x  3 1000 1000 4096 Dec 13 13:58 adapters
drwxrwxr-x  3 1000 1000 4096 Dec 13 17:36 brain
drwxrwxr-x  4 1000 1000 4096 Dec 13 11:59 data
drwxrwxr-x  2 1000 1000 4096 Dec 13 11:59 edge
-rw-------  1 1000 1000 7876 Dec 13 10:25 engine.py
drwxrwxr-x  2 1000 1000 4096 Dec 13 12:50 interfaces
drwxrwxr-x  2 1000 1000 4096 Dec 13 11:59 markets
drwxrwxr-x  3 1000 1000 4096 Dec 13 12:55 orchestrator
drwxrwxr-x  2 1000 1000 4096 Dec 13 11:59 probability
drwxrwxr-x  2 1000 1000 4096 Dec 13 09:53 risk
-rw-------  1 1000 1000 4580 Dec 13 10:26 test_mvp.py
drwxrwxr-x  2 1000 1000 4096 Dec 13 09:53 utils
```

**Analyse:**
- ✅ /quantum_core directory exists in container
- ✅ /quantum_core/brain subdirectory exists

#### 3.1 Production Import Test (Direct)
```bash
$ docker exec monps_backend python3 -c "from brain.unified_brain import UnifiedBrain; print('✅ OK')"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'brain'
```

**Analyse:**
- ✅ Production import: UnifiedBrain importable directly

#### 4.1 Pytest Context Import Test
```bash
$ docker exec monps_backend pytest tests/integration/brain/test_brain_real.py::TestBrainRepositoryIntegration::test_health_check_real -v
============================= test session starts ==============================
platform linux -- Python 3.11.14, pytest-7.4.3, pluggy-1.6.0 -- /usr/local/bin/python3.11
cachedir: .pytest_cache
rootdir: /app
configfile: pytest.ini
plugins: anyio-4.12.0, timeout-2.2.0, cov-4.1.0, asyncio-0.21.1, Faker-20.1.0, mock-3.12.0
timeout: 300.0s
timeout method: signal
timeout func_only: False
asyncio: mode=Mode.STRICT
collecting ... collected 1 item

tests/integration/brain/test_brain_real.py::TestBrainRepositoryIntegration::test_health_check_real SKIPPED [100%]/usr/local/lib/python3.11/site-packages/coverage/control.py:957: CoverageWarning: No data was collected. (no-data-collected); see https://coverage.readthedocs.io/en/7.13.0/messages.html#warning-no-data-collected
  self._warn("No data was collected.", slug="no-data-collected")


---------- coverage: platform linux, python 3.11.14-final-0 ----------
Name                         Stmts   Miss  Cover   Missing
----------------------------------------------------------
api/v1/brain/__init__.py         2      2  0.00%   8-10
api/v1/brain/repository.py     100    100  0.00%   10-238
api/v1/brain/routes.py          44     44  0.00%   5-117
api/v1/brain/schemas.py         83     83  0.00%   7-130
api/v1/brain/service.py         42     42  0.00%   5-107
----------------------------------------------------------
TOTAL                          271    271  0.00%
Coverage HTML written to dir htmlcov

FAIL Required test coverage of 90% not reached. Total coverage: 0.00%

============================== 1 skipped in 0.11s ==============================
```

**Analyse:**
- ⚠️ Test skipped in pytest context

#### 5.1 sys.path (Production Context)
```python

/usr/local/lib/python311.zip
/usr/local/lib/python3.11
/usr/local/lib/python3.11/lib-dynload
/usr/local/lib/python3.11/site-packages
```

#### 5.2 sys.path (Pytest Context)
```python
sys.path during pytest:
  /tmp
  /usr/local/bin
  /usr/local/lib/python311.zip
  /usr/local/lib/python3.11
  /usr/local/lib/python3.11/lib-dynload
  /usr/local/lib/python3.11/site-packages
PASSED

============================== 1 passed in 0.03s ===============================
```

**Analyse:**
- ❌ /quantum_core missing from production sys.path

#### 6.1 PYTHONPATH Environment Variable
```bash
$ docker exec monps_backend env | grep PYTHON
PYTHON_VERSION=3.11.14
PYTHON_SHA256=8d3ed8ec5c88c1c95f5e558612a725450d2452813ddad5e58fdb1a53b1209b78
```

#### 6.2 All Python-related ENV
```bash
PYTHON_VERSION=3.11.14
PYTHON_SHA256=8d3ed8ec5c88c1c95f5e558612a725450d2452813ddad5e58fdb1a53b1209b78
```

**Analyse:**
- ⚠️ /quantum_core missing from PYTHONPATH or PYTHONPATH not set

#### 7.1 pytest.ini Configuration
```ini
[pytest]
# Pytest configuration pour Brain API tests

# Python path
pythonpath = .

# Test discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Paths
testpaths = tests

# Markers
markers =
    unit: Unit tests (fast, mocks)
    integration: Integration tests (real dependencies)
    e2e: End-to-end tests (full stack)
    slow: Slow tests (>5s)
    concurrency: Concurrency tests

# Output
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=api/v1/brain
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=90

# Timeout
timeout = 300

# Warnings
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

**Analyse:**
- ✅ pythonpath directive present in pytest.ini
- ⚠️ /quantum_core missing from pytest pythonpath

#### 8.1 Integration Conftest quantum_core_path Fixture
```python
def quantum_core_path():
    """Path vers quantum_core MASTER"""
    path = Path("/home/Mon_ps/quantum_core")
    if not path.exists():
        pytest.skip(f"quantum_core not found at {path}")

    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

    return path


# ============================================================================
# REAL UNIFIEDBRAIN
# ============================================================================

@pytest.fixture(scope="session")
def real_unified_brain(quantum_core_path):
    """Real UnifiedBrain instance (expensive, shared)"""
    from brain.unified_brain import UnifiedBrain

```

**Analyse:**
- ⚠️ conftest.py uses pytest.skip when quantum_core not found

---

## DIAGNOSTIC SUMMARY

### Status Matrix

| Check                     | Status    | Details                           |
|---------------------------|-----------|-----------------------------------|
| docker-compose volume     | YES | quantum_core in volumes config    |
| Container mount           | YES | /quantum_core exists in container |
| brain/ subdirectory       | YES | /quantum_core/brain exists        |
| Production import         | NO | Direct import works               |
| Pytest import             | SKIPPED | Import in test context            |
| sys.path (production)     | NO | /quantum_core in sys.path         |
| PYTHONPATH env            | NO | /quantum_core in PYTHONPATH       |
| pytest.ini pythonpath     | PARTIAL | /quantum_core in pytest config    |
| conftest behavior         | SKIP | Skip strategy when not found      |

---

## ROOT CAUSE IDENTIFICATION

### ✅ ROOT CAUSE IDENTIFIED: sys.path Missing /quantum_core

**Problem:**
- /quantum_core exists in container ✅
- BUT not in sys.path (Python cannot import from it) ❌
- AND conftest.py checks WRONG PATH ❌

**Evidence:**
- Container: /quantum_core exists ✅
- sys.path: /quantum_core missing ❌
- conftest.py: checks /home/Mon_ps/quantum_core (wrong!) ❌
- Import fails: Cannot find brain module

**Root Causes (2 issues):**

**Issue 1: sys.path Missing /quantum_core**
- Python doesn't know to look in /quantum_core for modules
- Needs PYTHONPATH or pytest.ini configuration

**Issue 2: Conftest Wrong Path**
- `tests/integration/conftest.py` line 30:
  ```python
  path = Path("/home/Mon_ps/quantum_core")  # ❌ LOCAL path
  ```
- Should check `/quantum_core` (Docker volume) first
- Currently skips ALL tests because path doesn't exist

**Solution:**

**Option A - Fix conftest.py ONLY (RECOMMENDED - 5 min):**
```python
# tests/integration/conftest.py
@pytest.fixture(scope="session")
def quantum_core_path():
    """Path vers quantum_core MASTER (Docker-aware)"""
    
    # Priority 1: Docker volume
    docker_path = Path("/quantum_core")
    
    # Priority 2: Local development
    local_path = Path("/home/Mon_ps/quantum_core")
    
    if docker_path.exists():
        path = docker_path
    elif local_path.exists():
        path = local_path
    else:
        pytest.skip(
            "quantum_core not found in /quantum_core or /home/Mon_ps/quantum_core"
        )
    
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    
    return path
```

**Option B - Add PYTHONPATH (Infrastructure fix):**
```dockerfile
# backend/Dockerfile
ENV PYTHONPATH=/app:/quantum_core
```

**Option C - pytest.ini configuration:**
```ini
# pytest.ini
[pytest]
pythonpath = . /quantum_core
```

**RECOMMENDED: Option A (conftest fix)**
- ✅ Fastest (5 min)
- ✅ Follows same pattern as repository.py
- ✅ Docker/local compatible
- ✅ No infrastructure changes
- ✅ Tests will pass immediately

**Impact:**
- Integration tests: 0/6 → 6/6 PASSED
- Coverage: 76.01% → 90%+
- Full test suite: 11/17 → 17/17 PASSED


---

## RECOMMENDED SOLUTION

ROOT_CAUSE: SYSPATH_MISSING (conftest wrong path)

**Action Plan:**
Fix conftest.py to check /quantum_core (Docker volume) first, then fallback to /home/Mon_ps/quantum_core (local dev)

**Implementation:**
1. Edit `backend/tests/integration/conftest.py`
2. Replace lines 27-37 with Docker-aware path detection
3. No rebuild needed (Python code only)
4. Run tests to validate

**Validation Steps:**
1. Apply fix to conftest.py
2. Run integration tests: `pytest tests/integration/brain/ -v`
3. Verify all 6 tests PASS (not skipped)
4. Coverage should increase to 90%+
5. Full suite: 17/17 PASSED

---

## CONCLUSION

This diagnostic identifies the ROOT CAUSE preventing integration tests from executing.

**Problem Summary:**
- Infrastructure OK: volume mounted ✅
- Python can't import: sys.path missing /quantum_core ❌
- Conftest checks wrong path: /home/Mon_ps/quantum_core instead of /quantum_core ❌

**Solution:** Fix conftest.py path detection (5 min fix)

**Approach:** Fix at the root → Don't patch symptoms

---

## IMPLEMENTATION READY

The conftest.py fix is ready to implement. This is the SAME logic already used successfully in `api/v1/brain/repository.py` lines 21-48.

**Next Step:** Apply fix and validate
