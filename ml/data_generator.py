"""Synthetic banking dataset generator (demo data only — no real accounts, PINs, or cards)."""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from config import Config

REGIONS = {
    "North": ["Delhi", "Chandigarh", "Jaipur", "Lucknow", "Noida"],
    "South": ["Bengaluru", "Chennai", "Hyderabad", "Kochi", "Coimbatore"],
    "West": ["Mumbai", "Pune", "Ahmedabad", "Surat", "Nagpur"],
    "East": ["Kolkata", "Bhubaneswar", "Patna", "Ranchi", "Guwahati"],
}
FIRST_NAMES = [
    "Aarav", "Ananya", "Rohan", "Diya", "Kabir", "Isha", "Vihaan", "Meera",
    "Arjun", "Sneha", "Aditya", "Priya", "Rahul", "Kavya", "Nikhil", "Anusha",
    "Sanjay", "Neha", "Karan", "Pooja", "Amit", "Riya", "Vikram", "Shreya",
]
LAST_NAMES = [
    "Sharma", "Patel", "Reddy", "Nair", "Gupta", "Iyer", "Khan", "Das",
    "Mehta", "Joshi", "Singh", "Pillai", "Rao", "Verma", "Banerjee", "Kulkarni",
]
OCCUPATIONS = ["Salaried", "Self-employed", "Professional", "Student", "Retired", "Business"]
ACCOUNT_TYPES = ["Savings", "Current", "Salary", "NRI"]
INCOME_BANDS = ["Low", "Medium", "High", "Premium"]
TXN_TYPES = ["Deposit", "Withdrawal", "Transfer", "BillPay", "Card"]
CHANNELS = ["Branch", "ATM", "Mobile", "Internet", "Card"]
MANAGERS = ["R. Krishnan", "S. Banerjee", "M. Fernandes", "P. Deshmukh", "L. Thomas"]


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_branches(n_branches: int, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    region_names = list(REGIONS.keys())
    for i in range(n_branches):
        region = region_names[i % len(region_names)]
        city = REGIONS[region][i % len(REGIONS[region])]
        rows.append(
            {
                "branch_id": f"BR{i + 1:03d}",
                "branch_name": f"{city} {['Central', 'Plaza', 'Metro', 'City', 'Prime'][i % 5]} Branch",
                "region": region,
                "city": city,
                "manager_name": MANAGERS[i % len(MANAGERS)],
                "opened_year": int(rng.integers(1998, 2022)),
                "staff_count": int(rng.integers(8, 42)),
            }
        )
    return pd.DataFrame(rows)


def generate_customers(n_customers: int, branches: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    n = n_customers
    ages = rng.integers(21, 72, n)
    genders = rng.choice(["Female", "Male", "Other"], n, p=[0.47, 0.51, 0.02])
    branch_ids = rng.choice(branches["branch_id"].tolist(), n)
    branch_map = branches.set_index("branch_id")[["city", "region"]].to_dict("index")
    account_types = rng.choice(ACCOUNT_TYPES, n, p=[0.55, 0.18, 0.22, 0.05])
    tenure = rng.integers(4, 180, n)
    products = rng.integers(1, 7, n)
    credit = np.clip(rng.normal(710, 70, n).astype(int), 480, 850)
    occupations = rng.choice(OCCUPATIONS, n)
    income = rng.choice(INCOME_BANDS, n, p=[0.22, 0.45, 0.25, 0.08])
    satisfaction = np.clip(rng.normal(3.6, 0.9, n), 1.0, 5.0).round(2)
    complaints = rng.poisson(0.7, n)
    service_req = rng.poisson(1.4, n)
    latent = np.clip(
        0.18 * (complaints >= 2).astype(float)
        + 0.16 * (satisfaction < 2.8).astype(float)
        + 0.10 * (tenure < 12).astype(float)
        + 0.08 * (credit < 620).astype(float)
        + 0.08 * (products == 1).astype(float)
        + rng.normal(0, 0.08, n),
        0,
        0.85,
    )
    names = [
        f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[(i * 7) % len(LAST_NAMES)]}"
        for i in range(n)
    ]
    open_dates = [
        (datetime(2025, 8, 1) - timedelta(days=int(t) * 30)).date().isoformat()
        for t in tenure
    ]
    rows = []
    for i in range(n):
        b = branch_map[branch_ids[i]]
        rows.append(
            {
                "customer_id": f"CUST{i + 1:06d}",
                "full_name": names[i],
                "age": int(ages[i]),
                "gender": genders[i],
                "city": b["city"],
                "region": b["region"],
                "branch_id": branch_ids[i],
                "account_type": account_types[i],
                "masked_account": f"ACC-****{1000 + (i % 9000)}",
                "account_open_date": open_dates[i],
                "tenure_months": int(tenure[i]),
                "products_count": int(products[i]),
                "credit_score": int(credit[i]),
                "occupation": occupations[i],
                "income_band": income[i],
                "satisfaction_score": float(satisfaction[i]),
                "complaint_count": int(complaints[i]),
                "service_request_count": int(service_req[i]),
                "latent_risk": float(latent[i]),
                "churn_label": 0,
            }
        )
    return pd.DataFrame(rows)


def generate_behaviour(customers: pd.DataFrame, n_months: int, rng: np.random.Generator) -> pd.DataFrame:
    month_labels = pd.period_range("2024-09", periods=n_months, freq="M").astype(str).tolist()
    income_mult = {"Low": 0.6, "Medium": 1.0, "High": 1.7, "Premium": 2.8}
    rows = []
    for _, c in customers.iterrows():
        risk = c["latent_risk"]
        base_freq = max(2, rng.normal(12, 4) * income_mult[c["income_band"]])
        base_amt = max(4000, rng.normal(28000, 9000) * income_mult[c["income_band"]])
        base_bal = max(8000, rng.normal(120000, 40000) * income_mult[c["income_band"]])
        mobile = max(2, rng.normal(18, 6))
        internet = max(1, rng.normal(10, 4))
        atm = max(0, rng.normal(4, 2))
        card = max(1, rng.normal(9, 3))
        shift_customer = rng.random() < (0.18 + risk)
        drop_start = int(rng.integers(8, 11)) if shift_customer else 99
        for m in range(n_months):
            decay = 1.0
            if m >= drop_start:
                decay = max(0.25, 1.0 - (m - drop_start + 1) * (0.18 + risk))
            noise = rng.normal(1.0, 0.08)
            freq = max(0, int(base_freq * decay * noise))
            amt = max(0.0, float(base_amt * decay * noise))
            dep = amt * float(rng.uniform(0.45, 0.7))
            wdr = amt - dep
            mob = max(0, int(mobile * decay * rng.normal(1.0, 0.1)))
            inet = max(0, int(internet * decay * rng.normal(1.0, 0.1)))
            atm_u = max(0, int(atm * (1.2 - 0.4 * decay) * rng.normal(1.0, 0.1)))
            card_u = max(0, int(card * decay * rng.normal(1.0, 0.1)))
            bal = max(500.0, float(base_bal * decay * rng.normal(1.0, 0.06)))
            digital = float(np.clip((mob + inet) / 40.0 * 100, 0, 100))
            complaints = int(rng.poisson(0.15 + (0.6 if decay < 0.7 else 0) + risk))
            service = int(rng.poisson(0.3 + (0.4 if decay < 0.8 else 0)))
            rows.append(
                {
                    "customer_id": c["customer_id"],
                    "month_index": m + 1,
                    "month_label": month_labels[m],
                    "txn_frequency": freq,
                    "txn_amount": round(amt, 2),
                    "deposits": round(dep, 2),
                    "withdrawals": round(wdr, 2),
                    "atm_usage": atm_u,
                    "mobile_usage": mob,
                    "internet_usage": inet,
                    "card_usage": card_u,
                    "avg_balance": round(bal, 2),
                    "digital_engagement": round(digital, 2),
                    "complaints": complaints,
                    "service_activity": service,
                }
            )
    return pd.DataFrame(rows)


def finalize_churn_labels(customers: pd.DataFrame, behaviour: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    hist = behaviour[behaviour["month_index"] <= 9].groupby("customer_id")[
        ["txn_frequency", "avg_balance", "digital_engagement"]
    ].mean()
    rec = behaviour[behaviour["month_index"] >= 10].groupby("customer_id")[
        ["txn_frequency", "avg_balance", "digital_engagement", "complaints"]
    ].mean()
    joined = hist.join(rec, lsuffix="_h", rsuffix="_r")
    freq_drop = (joined["txn_frequency_h"] - joined["txn_frequency_r"]) / (joined["txn_frequency_h"] + 1)
    bal_drop = (joined["avg_balance_h"] - joined["avg_balance_r"]) / (joined["avg_balance_h"] + 1)
    dig_drop = (joined["digital_engagement_h"] - joined["digital_engagement_r"]) / (joined["digital_engagement_h"] + 1)
    score = (
        customers.set_index("customer_id")["latent_risk"]
        + 0.35 * freq_drop.clip(lower=0)
        + 0.25 * bal_drop.clip(lower=0)
        + 0.20 * dig_drop.clip(lower=0)
        + 0.08 * (rec["complaints"] > 0.8).astype(float)
    )
    prob = 1 / (1 + np.exp(-6 * (score - 0.42)))
    labels = (rng.random(len(prob)) < prob.reindex(customers["customer_id"]).values).astype(int)
    customers = customers.copy()
    customers["churn_label"] = labels
    return customers.drop(columns=["latent_risk"])


def generate_engagement(customers: pd.DataFrame, behaviour: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rec = behaviour[behaviour["month_index"] >= 10].groupby("customer_id").agg(
        mobile_usage=("mobile_usage", "sum"),
        internet_usage=("internet_usage", "sum"),
        digital_engagement=("digital_engagement", "mean"),
    )
    rows = []
    for _, c in customers.iterrows():
        r = rec.loc[c["customer_id"]]
        last_login = int(rng.integers(1, 12) if r["digital_engagement"] > 40 else rng.integers(8, 75))
        if c["churn_label"] == 1:
            last_login = max(last_login, int(rng.integers(20, 90)))
        rows.append(
            {
                "customer_id": c["customer_id"],
                "mobile_logins": int(r["mobile_usage"]),
                "internet_logins": int(r["internet_usage"]),
                "app_sessions": int(r["mobile_usage"] + rng.integers(0, 8)),
                "last_login_days": last_login,
                "nps_score": float(np.clip(c["satisfaction_score"] * 20 + rng.normal(0, 6), 0, 100)),
                "product_usage_score": float(np.clip(c["products_count"] * 14 + rng.normal(0, 8), 5, 100)),
                "digital_active": int(r["digital_engagement"] >= 35),
            }
        )
    return pd.DataFrame(rows)


def generate_transactions(
    customers: pd.DataFrame,
    behaviour: pd.DataFrame,
    n_transactions: int,
    rng: np.random.Generator,
) -> pd.DataFrame:
    cust_ids = customers["customer_id"].to_numpy()
    branch_of = customers.set_index("customer_id")["branch_id"]
    weights = behaviour.groupby("customer_id")["txn_frequency"].mean()
    weights = (weights / weights.sum()).reindex(customers["customer_id"]).fillna(1 / len(customers)).to_numpy()
    chosen = rng.choice(cust_ids, size=n_transactions, p=weights)
    days = rng.integers(0, 365, n_transactions)
    start = np.datetime64("2024-09-01")
    dates = (start + days.astype("timedelta64[D]")).astype(str)
    ttypes = rng.choice(TXN_TYPES, size=n_transactions, p=[0.28, 0.27, 0.2, 0.12, 0.13])
    channels = rng.choice(CHANNELS, size=n_transactions, p=[0.12, 0.18, 0.38, 0.18, 0.14])
    amounts = np.clip(rng.lognormal(mean=8.2, sigma=0.9, size=n_transactions), 50, None)
    return pd.DataFrame(
        {
            "txn_id": [f"TXN{i + 1:08d}" for i in range(n_transactions)],
            "customer_id": chosen,
            "branch_id": branch_of.loc[chosen].to_numpy(),
            "txn_date": dates,
            "txn_type": ttypes,
            "channel": channels,
            "amount": np.round(amounts, 2),
        }
    )


def generate_all(output_dir: str | None = None) -> dict[str, pd.DataFrame]:
    rng = _rng(Config.RANDOM_STATE)
    branches = generate_branches(Config.N_BRANCHES, rng)
    customers = generate_customers(Config.N_CUSTOMERS, branches, rng)
    behaviour = generate_behaviour(customers, Config.N_MONTHS, rng)
    customers = finalize_churn_labels(customers, behaviour, rng)
    engagement = generate_engagement(customers, behaviour, rng)
    transactions = generate_transactions(customers, behaviour, Config.N_TRANSACTIONS, rng)
    frames = {
        "branches": branches,
        "customers": customers,
        "customer_behaviour": behaviour,
        "customer_engagement": engagement,
        "transactions": transactions,
    }
    out = output_dir or Config.DATASET_DIR
    os.makedirs(out, exist_ok=True)
    for name, df in frames.items():
        df.to_csv(os.path.join(out, f"{name}.csv"), index=False)
    return frames
