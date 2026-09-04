"""Generate the deterministic Payments Analytics v2 synthetic snapshot.

Settlement outcomes are derived from effective merchant terms. Four guided
close-day scenarios are placed deterministically; no row represents a real
customer, merchant, payment, incident, or business result.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import random
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from faker import Faker

SEED = 42
NUM_CUSTOMERS = 5_000
NUM_ACCOUNTS = 6_000
NUM_MERCHANTS = 800
NUM_TRANSACTIONS = 80_000
NUM_FRAUD_FLAGS = 2_500
START_DATE = dt.date(2022, 1, 1)
END_DATE = dt.date(2024, 12, 31)

DATA_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DATA_DIR / "raw"
SCENARIO_MANIFEST = DATA_DIR / "scenarios.json"
SCENARIO_BATCH_SIZE = 48
TERMS_CHANGE_DATE = dt.date(2024, 10, 1)

COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Germany", "France",
    "Australia", "Singapore", "India", "Japan", "Brazil",
]
MERCHANT_CATEGORIES = [
    "Retail", "Travel", "Entertainment", "Electronics", "Utilities",
    "Food & Beverage", "Services", "Healthcare",
]
FRAUD_REASONS = [
    "Velocity Limit Exceeded", "High Risk Country Match",
    "Suspicious Amount Spike", "Mismatched Billing Details",
    "Card-Not-Present Anomaly",
]

_fake = Faker()
_scenario_assignments: dict[str, list[int]] = {}


def reset_seed() -> None:
    """Reset all random sources so repeated calls are byte-stable."""
    global _fake, _scenario_assignments
    random.seed(SEED)
    Faker.seed(SEED)
    _fake = Faker()
    _scenario_assignments = {}


def _manifest() -> dict[str, Any]:
    return json.loads(SCENARIO_MANIFEST.read_text(encoding="utf-8"))


def _write_rows(filename: str, rows: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty source table: {filename}")
    destination = OUTPUT_DIR / filename
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(destination)


def _money(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def get_random_date(start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=random.randint(0, (end - start).days))


def get_random_timestamp(start: dt.date, end: dt.date) -> dt.datetime:
    return dt.datetime.combine(
        get_random_date(start, end),
        dt.time(random.randint(0, 23), random.randint(0, 59), random.randint(0, 59)),
    )


def generate_customers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for customer_id in range(1, NUM_CUSTOMERS + 1):
        name = _fake.name()
        rows.append({
            "customer_id": customer_id,
            "full_name": name,
            "email": f"{name.lower().replace(' ', '').replace('.', '')}_{customer_id}@example.com",
            "country": random.choice(COUNTRIES),
            "join_date": get_random_date(START_DATE, END_DATE).isoformat(),
            "segment": random.choices(
                ["retail", "business", "premium"], weights=[.80, .15, .05], k=1
            )[0],
            "is_active": random.choices([True, False], weights=[.90, .10], k=1)[0],
        })
    _write_rows("customers.csv", rows)
    return rows


def generate_accounts(customers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(customer: dict[str, Any]) -> None:
        # Keep the original generator's draw order stable so v1 source counts
        # remain comparable after the deterministic scenario overlay.
        opened_date = get_random_date(
            dt.date.fromisoformat(customer["join_date"]), END_DATE
        ).isoformat()
        account_type = random.choices(
            ["current", "savings", "merchant"], weights=[.60, .35, .05], k=1
        )[0]
        currency = random.choice(["EUR", "EUR", "GBP", "AUD", "CAD"])
        status = random.choices(
            ["active", "closed", "suspended"], weights=[.92, .05, .03], k=1
        )[0]
        rows.append({
            "account_id": len(rows) + 1,
            "customer_id": customer["customer_id"],
            "account_type": account_type,
            "currency": currency,
            "opened_date": opened_date,
            "status": status,
        })

    for customer in customers:
        add(customer)
    while len(rows) < NUM_ACCOUNTS:
        add(random.choice(customers))
    _write_rows("accounts.csv", rows)
    return rows


def generate_merchants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for merchant_id in range(1, NUM_MERCHANTS + 1):
        rows.append({
            "merchant_id": merchant_id,
            "merchant_name": _fake.company(),
            "category": random.choice(MERCHANT_CATEGORIES),
            "country": random.choice(COUNTRIES),
            "registration_date": get_random_date(START_DATE, END_DATE).isoformat(),
            "risk_tier": random.choices(
                ["low", "medium", "high"], weights=[.85, .12, .03], k=1
            )[0],
        })
    _write_rows("merchants.csv", rows)
    return rows


def _place_scenarios(
    transactions: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    merchants: list[dict[str, Any]],
) -> None:
    account_by_id = {row["account_id"]: row for row in accounts}
    merchant_by_id = {row["merchant_id"]: row for row in merchants}
    used: set[int] = set()
    specs = {
        row["scenarioId"]: (
            row["focusCategory"],
            row["defaultCurrency"],
            dt.date.fromisoformat(row["closeDate"]),
        )
        for row in _manifest()["scenarios"]
    }
    for scenario_id, (category, currency, close_date) in specs.items():
        candidates: list[dict[str, Any]] = []
        for tx in transactions:
            merchant_id = tx["merchant_id"]
            if (
                tx["transaction_id"] in used
                or tx["status"] != "completed"
                or tx["transaction_type"] != "purchase"
                or merchant_id == ""
            ):
                continue
            account, merchant = account_by_id[tx["account_id"]], merchant_by_id[merchant_id]
            if (
                account["currency"] == currency
                and merchant["category"] == category
                and dt.date.fromisoformat(account["opened_date"]) <= close_date
                and dt.date.fromisoformat(merchant["registration_date"]) <= close_date
                and (
                    scenario_id != "stale_electronics_eur_fee"
                    or (
                        Decimal(tx["amount"]) >= Decimal("100.00")
                        and dt.date.fromisoformat(merchant["registration_date"])
                            <= TERMS_CHANGE_DATE
                    )
                )
            ):
                candidates.append(tx)
                if len(candidates) == SCENARIO_BATCH_SIZE:
                    break
        if len(candidates) != SCENARIO_BATCH_SIZE:
            raise RuntimeError(f"Not enough eligible rows for {scenario_id}")
        ids: list[int] = []
        for offset, tx in enumerate(candidates):
            tx["transaction_date"] = dt.datetime.combine(
                close_date,
                dt.time(9 + offset % 8, offset * 7 % 60, offset * 13 % 60),
            ).strftime("%Y-%m-%d %H:%M:%S")
            used.add(tx["transaction_id"])
            ids.append(tx["transaction_id"])
        _scenario_assignments[scenario_id] = ids

    scenario_dates = {value[2] for value in specs.values()}
    promoted: list[int] = []
    for tx in transactions:
        tx_date = dt.datetime.strptime(tx["transaction_date"], "%Y-%m-%d %H:%M:%S").date()
        if (
            tx["status"] == "pending"
            and tx["transaction_type"] == "purchase"
            and tx["merchant_id"] != ""
            and tx_date not in scenario_dates
        ):
            tx["status"] = "completed"
            promoted.append(tx["transaction_id"])
            if len(promoted) == SCENARIO_BATCH_SIZE:
                break
    if len(promoted) != SCENARIO_BATCH_SIZE:
        raise RuntimeError("Not enough pending purchases to offset the missing batch")
    _scenario_assignments["promoted_controls"] = promoted


def generate_transactions(
    accounts: list[dict[str, Any]], merchants: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    account_by_id = {row["account_id"]: row for row in accounts}
    merchant_by_id = {row["merchant_id"]: row for row in merchants}
    for transaction_id in range(1, NUM_TRANSACTIONS + 1):
        account_id = random.randint(1, len(accounts))
        account = account_by_id[account_id]
        tx_time = get_random_timestamp(dt.date.fromisoformat(account["opened_date"]), END_DATE)
        tx_type = random.choices(
            ["purchase", "refund", "transfer"], weights=[.80, .05, .15], k=1
        )[0]
        merchant_id: int | str = ""
        if tx_type in ("purchase", "refund"):
            merchant_id = random.randint(1, len(merchants))
            registered = dt.date.fromisoformat(merchant_by_id[merchant_id]["registration_date"])
            if tx_time.date() < registered:
                tx_time = get_random_timestamp(registered, END_DATE)
        low, high = (5.0, 300.0) if tx_type == "refund" else (1.0, 5_000.0)
        rows.append({
            "transaction_id": transaction_id,
            "account_id": account_id,
            "merchant_id": merchant_id,
            "amount": f"{random.uniform(low, high):.2f}",
            "currency": account["currency"],
            "transaction_date": tx_time.strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_type": tx_type,
            "status": random.choices(
                ["completed", "failed", "pending"], weights=[.90, .08, .02], k=1
            )[0],
        })
    _place_scenarios(rows, accounts, merchants)
    _write_rows("transactions.csv", rows)
    return rows


def _base_term(merchant: dict[str, Any]) -> tuple[int, int]:
    return {"low": (150, 2), "medium": (250, 3), "high": (400, 5)}[
        merchant["risk_tier"]
    ]


def generate_merchant_terms(
    merchants: list[dict[str, Any]], transactions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    tx_by_id = {row["transaction_id"]: row for row in transactions}
    stale_merchants = {
        tx_by_id[tx_id]["merchant_id"]
        for tx_id in _scenario_assignments["stale_electronics_eur_fee"]
    }
    change_date = TERMS_CHANGE_DATE
    rows: list[dict[str, Any]] = []
    for merchant in merchants:
        fee_bps, sla_days = _base_term(merchant)
        common = {
            "merchant_id": merchant["merchant_id"],
            "valid_from": merchant["registration_date"],
            "fee_rate_bps": fee_bps,
            "settlement_sla_days": sla_days,
        }
        if merchant["merchant_id"] in stale_merchants:
            rows.append({
                **common,
                "valid_to": (change_date - dt.timedelta(days=1)).isoformat(),
            })
            rows.append({
                **common,
                "valid_from": change_date.isoformat(),
                "valid_to": "",
                "fee_rate_bps": fee_bps - 40,
            })
        else:
            rows.append({**common, "valid_to": ""})
    rows.sort(key=lambda row: (row["merchant_id"], row["valid_from"]))
    _write_rows("merchant_terms.csv", rows)
    return rows


def _effective_term(
    terms_by_merchant: dict[int, list[dict[str, Any]]],
    merchant_id: int,
    tx_date: dt.date,
) -> dict[str, Any]:
    matches = []
    for term in terms_by_merchant[merchant_id]:
        valid_to = dt.date.fromisoformat(term["valid_to"]) if term["valid_to"] else dt.date.max
        if dt.date.fromisoformat(term["valid_from"]) <= tx_date <= valid_to:
            matches.append(term)
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one term for merchant {merchant_id} on {tx_date}; got {len(matches)}"
        )
    return matches[0]


def generate_settlements(
    transactions: list[dict[str, Any]],
    merchants: list[dict[str, Any]],
    merchant_terms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merchant_by_id = {row["merchant_id"]: row for row in merchants}
    terms_by_merchant: dict[int, list[dict[str, Any]]] = {}
    for term in merchant_terms:
        terms_by_merchant.setdefault(term["merchant_id"], []).append(term)
    missing_ids = set(_scenario_assignments["missing_retail_cad"])
    stale_ids = set(_scenario_assignments["stale_electronics_eur_fee"])
    delayed_scenario_ids = set(_scenario_assignments["delayed_travel_gbp"])
    all_scenario_ids = set().union(*(
        set(_scenario_assignments[key])
        for key in (
            "normal", "delayed_travel_gbp", "stale_electronics_eur_fee",
            "missing_retail_cad",
        )
    ))
    eligible = [
        tx for tx in transactions if tx["status"] == "completed" and tx["merchant_id"] != ""
    ]
    rows: list[dict[str, Any]] = []
    by_tx: dict[int, dict[str, Any]] = {}
    for tx in eligible:
        tx_id = tx["transaction_id"]
        if tx_id in missing_ids:
            continue
        tx_time = dt.datetime.strptime(tx["transaction_date"], "%Y-%m-%d %H:%M:%S")
        term = _effective_term(terms_by_merchant, tx["merchant_id"], tx_time.date())
        applied_bps = int(term["fee_rate_bps"]) + (40 if tx_id in stale_ids else 0)
        gross = _money(tx["amount"])
        fee = _money(gross * Decimal(applied_bps) / Decimal(10_000))
        sla_days = int(term["settlement_sla_days"])
        settle_days = sla_days + 3 if tx_id in delayed_scenario_ids else 1 + tx_id % sla_days
        row = {
            "settlement_id": len(rows) + 1,
            "transaction_id": tx_id,
            "settlement_date": (tx_time + dt.timedelta(days=settle_days)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "currency": tx["currency"],
            "settled_amount": f"{gross - fee:.2f}",
            "processing_fee": f"{fee:.2f}",
            "status": "settled",
        }
        rows.append(row)
        by_tx[tx_id] = row

    tx_by_id = {row["transaction_id"]: row for row in transactions}
    guided_dates = {
        dt.datetime.strptime(
            tx_by_id[tx_id]["transaction_date"], "%Y-%m-%d %H:%M:%S"
        ).date()
        for key in (
            "normal", "delayed_travel_gbp", "stale_electronics_eur_fee",
            "missing_retail_cad",
        )
        for tx_id in _scenario_assignments[key]
    }
    risk_rank = {"high": 0, "medium": 1, "low": 2}
    candidates = sorted(
        (
            row for row in rows
            if row["transaction_id"] not in all_scenario_ids
            and dt.datetime.strptime(
                tx_by_id[row["transaction_id"]]["transaction_date"],
                "%Y-%m-%d %H:%M:%S",
            ).date() not in guided_dates
        ),
        key=lambda row: (
            risk_rank[merchant_by_id[tx_by_id[row["transaction_id"]]["merchant_id"]]["risk_tier"]],
            -int(Decimal(tx_by_id[row["transaction_id"]]["amount"]) * 100),
            row["transaction_id"],
        ),
    )
    disputed = candidates[:6]
    for row in disputed:
        row["status"] = "disputed"
    for tx_id in delayed_scenario_ids:
        by_tx[tx_id]["status"] = "delayed"

    # Deterministic controls prove the mismatch rules outside guided dates.
    controls = [
        row for row in rows
        if row["status"] == "settled"
        and row["transaction_id"] not in all_scenario_ids
        and tx_by_id[row["transaction_id"]]["transaction_type"] == "purchase"
        and dt.datetime.strptime(
            tx_by_id[row["transaction_id"]]["transaction_date"],
            "%Y-%m-%d %H:%M:%S",
        ).date() not in guided_dates
    ]
    currency_cycle = {"EUR": "GBP", "GBP": "EUR", "AUD": "CAD", "CAD": "AUD"}
    for row in controls[:6]:
        row["currency"] = currency_cycle[row["currency"]]
    for row in controls[6:12]:
        row["settled_amount"] = f"{_money(row['settled_amount']) - Decimal('0.25'):.2f}"
    _scenario_assignments["currency_mismatch_controls"] = [
        row["transaction_id"] for row in controls[:6]
    ]
    _scenario_assignments["amount_mismatch_controls"] = [
        row["transaction_id"] for row in controls[6:12]
    ]

    actual = {
        status: sum(row["status"] == status for row in rows)
        for status in ("settled", "delayed", "disputed")
    }
    expected = {"settled": 61_070, "delayed": 48, "disputed": 6}
    if actual != expected:
        raise RuntimeError(f"Settlement status drift: {actual} != {expected}")
    _write_rows("settlements.csv", rows)
    return rows


def generate_fraud_flags(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        transactions,
        key=lambda tx: (
            tx["transaction_type"] != "transfer",
            -int(Decimal(tx["amount"]) * 100),
            tx["transaction_id"],
        ),
    )[:NUM_FRAUD_FLAGS]
    rows: list[dict[str, Any]] = []
    for index, tx in enumerate(ranked, start=1):
        tx_time = dt.datetime.strptime(tx["transaction_date"], "%Y-%m-%d %H:%M:%S")
        flagged = tx_time + dt.timedelta(minutes=tx["transaction_id"] % 180 + 1)
        unresolved = index <= 486
        rows.append({
            "flag_id": index,
            "transaction_id": tx["transaction_id"],
            "flagged_date": flagged.strftime("%Y-%m-%d %H:%M:%S"),
            "flag_reason": FRAUD_REASONS[tx["transaction_id"] % len(FRAUD_REASONS)],
            "is_resolved": not unresolved,
            "resolved_date": "" if unresolved else (
                flagged + dt.timedelta(days=1 + tx["transaction_id"] % 7)
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })
    _write_rows("fraud_flags.csv", rows)
    return rows


def validate_generated_snapshot(tables: dict[str, list[dict[str, Any]]]) -> None:
    expected = {
        "customers": NUM_CUSTOMERS, "accounts": NUM_ACCOUNTS,
        "merchants": NUM_MERCHANTS, "transactions": NUM_TRANSACTIONS,
        "settlements": 61_124, "fraud_flags": NUM_FRAUD_FLAGS,
    }
    actual = {name: len(tables[name]) for name in expected}
    if actual != expected:
        raise RuntimeError(f"Source count drift: {actual} != {expected}")
    transaction_ids = {row["transaction_id"] for row in tables["transactions"]}
    merchant_ids = {row["merchant_id"] for row in tables["merchants"]}
    if any(row["transaction_id"] not in transaction_ids for row in tables["settlements"]):
        raise RuntimeError("Settlement references an unknown transaction")
    if any(row["merchant_id"] not in merchant_ids for row in tables["merchant_terms"]):
        raise RuntimeError("Merchant term references an unknown merchant")
    manifest_ids = {row["scenarioId"] for row in _manifest()["scenarios"]}
    if not manifest_ids.issubset(_scenario_assignments):
        raise RuntimeError("Scenario manifest and generated placements are out of sync")


def main() -> None:
    reset_seed()
    customers = generate_customers()
    accounts = generate_accounts(customers)
    merchants = generate_merchants()
    transactions = generate_transactions(accounts, merchants)
    merchant_terms = generate_merchant_terms(merchants, transactions)
    settlements = generate_settlements(transactions, merchants, merchant_terms)
    fraud_flags = generate_fraud_flags(transactions)
    validate_generated_snapshot({
        "customers": customers, "accounts": accounts, "merchants": merchants,
        "merchant_terms": merchant_terms, "transactions": transactions,
        "settlements": settlements, "fraud_flags": fraud_flags,
    })
    print(
        f"Generated deterministic synthetic snapshot {_manifest()['datasetVersion']} "
        f"in {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()
