#!/usr/bin/env python3
"""
Monte Carlo RÉALISTE avec WR 80% sur 100+ bets
"""
import random
import numpy as np

print("=" * 70)
print("    SIMULATION MONTE CARLO RÉALISTE")
print("=" * 70)

# Paramètres basés sur le backtest V11.3
scenarios = [
    {"name": "SNIPER (score 30+)", "wr": 0.95, "odds": 1.85, "bets_per_month": 5, "stake": 0.03},
    {"name": "GOLD (score 28-30)", "wr": 0.90, "odds": 1.85, "bets_per_month": 15, "stake": 0.025},
    {"name": "SILVER (score 26-28)", "wr": 0.85, "odds": 1.85, "bets_per_month": 20, "stake": 0.02},
    {"name": "BRONZE (score 24-26)", "wr": 0.67, "odds": 1.85, "bets_per_month": 30, "stake": 0.015},
]

N_SIMULATIONS = 10000
MONTHS = 12
INITIAL_BANKROLL = 1000

print(f"\n📊 Paramètres:")
print(f"   Simulations: {N_SIMULATIONS:,}")
print(f"   Durée: {MONTHS} mois")
print(f"   Bankroll initial: {INITIAL_BANKROLL}€")
print()

for scenario in scenarios:
    print(f"\n{'─' * 70}")
    print(f"📈 {scenario['name']}")
    print(f"   WR: {scenario['wr']*100:.0f}% | Odds: {scenario['odds']} | Stake: {scenario['stake']*100:.1f}%")
    print(f"   Bets/mois: {scenario['bets_per_month']}")
    
    final_bankrolls = []
    max_drawdowns = []
    
    for _ in range(N_SIMULATIONS):
        bankroll = INITIAL_BANKROLL
        peak = bankroll
        max_dd = 0
        
        for month in range(MONTHS):
            for bet in range(scenario['bets_per_month']):
                stake_amount = bankroll * scenario['stake']
                
                if random.random() < scenario['wr']:
                    # Win
                    bankroll += stake_amount * (scenario['odds'] - 1)
                else:
                    # Loss
                    bankroll -= stake_amount
                
                # Track drawdown
                if bankroll > peak:
                    peak = bankroll
                dd = (peak - bankroll) / peak
                if dd > max_dd:
                    max_dd = dd
                
                # Ruine check
                if bankroll <= 0:
                    break
            
            if bankroll <= 0:
                break
        
        final_bankrolls.append(bankroll)
        max_drawdowns.append(max_dd)
    
    # Statistiques
    final_bankrolls = np.array(final_bankrolls)
    max_drawdowns = np.array(max_drawdowns)
    
    mean_bankroll = np.mean(final_bankrolls)
    median_bankroll = np.median(final_bankrolls)
    p5 = np.percentile(final_bankrolls, 5)
    p95 = np.percentile(final_bankrolls, 95)
    prob_profit = np.mean(final_bankrolls > INITIAL_BANKROLL) * 100
    prob_ruin = np.mean(final_bankrolls <= 0) * 100
    mean_dd = np.mean(max_drawdowns) * 100
    
    roi = (mean_bankroll - INITIAL_BANKROLL) / INITIAL_BANKROLL * 100
    
    print(f"\n   Résultats sur {MONTHS} mois:")
    print(f"      💰 Bankroll moyenne: {mean_bankroll:,.0f}€ (ROI: {roi:+.0f}%)")
    print(f"      💰 Bankroll médiane: {median_bankroll:,.0f}€")
    print(f"      📉 Scénario pessimiste (P5): {p5:,.0f}€")
    print(f"      📈 Scénario optimiste (P95): {p95:,.0f}€")
    print(f"      ✅ Probabilité profit: {prob_profit:.1f}%")
    print(f"      ❌ Risque de ruine: {prob_ruin:.2f}%")
    print(f"      📊 Drawdown moyen: {mean_dd:.1f}%")

# Simulation combinée (tous les niveaux)
print(f"\n{'=' * 70}")
print("📊 SIMULATION COMBINÉE (toutes zones)")
print("=" * 70)

combined_bets = []
for s in scenarios:
    for _ in range(s['bets_per_month']):
        combined_bets.append({'wr': s['wr'], 'odds': s['odds'], 'stake': s['stake']})

total_bets_month = len(combined_bets)
print(f"   Total bets/mois: {total_bets_month}")

final_bankrolls = []
max_drawdowns = []

for _ in range(N_SIMULATIONS):
    bankroll = INITIAL_BANKROLL
    peak = bankroll
    max_dd = 0
    
    for month in range(MONTHS):
        random.shuffle(combined_bets)  # Mélanger l'ordre des bets
        
        for bet in combined_bets:
            stake_amount = bankroll * bet['stake']
            
            if random.random() < bet['wr']:
                bankroll += stake_amount * (bet['odds'] - 1)
            else:
                bankroll -= stake_amount
            
            if bankroll > peak:
                peak = bankroll
            dd = (peak - bankroll) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
            
            if bankroll <= 0:
                break
        
        if bankroll <= 0:
            break
    
    final_bankrolls.append(bankroll)
    max_drawdowns.append(max_dd)

final_bankrolls = np.array(final_bankrolls)
max_drawdowns = np.array(max_drawdowns)

mean_bankroll = np.mean(final_bankrolls)
median_bankroll = np.median(final_bankrolls)
p5 = np.percentile(final_bankrolls, 5)
p95 = np.percentile(final_bankrolls, 95)
prob_profit = np.mean(final_bankrolls > INITIAL_BANKROLL) * 100
prob_ruin = np.mean(final_bankrolls <= 0) * 100
mean_dd = np.mean(max_drawdowns) * 100
max_dd_worst = np.max(max_drawdowns) * 100
roi = (mean_bankroll - INITIAL_BANKROLL) / INITIAL_BANKROLL * 100

print(f"\n   📊 Résultats combinés ({total_bets_month} bets/mois × {MONTHS} mois = {total_bets_month * MONTHS} bets):")
print(f"      💰 Bankroll moyenne: {mean_bankroll:,.0f}€ (ROI: {roi:+.0f}%)")
print(f"      💰 Bankroll médiane: {median_bankroll:,.0f}€")
print(f"      📉 Scénario pessimiste (P5): {p5:,.0f}€")
print(f"      📈 Scénario optimiste (P95): {p95:,.0f}€")
print(f"      ✅ Probabilité profit: {prob_profit:.1f}%")
print(f"      ❌ Risque de ruine: {prob_ruin:.2f}%")
print(f"      📊 Drawdown moyen: {mean_dd:.1f}%")
print(f"      📊 Pire drawdown: {max_dd_worst:.1f}%")

print("\n" + "=" * 70)
