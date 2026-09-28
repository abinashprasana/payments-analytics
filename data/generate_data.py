"""Generate the deterministic Payments Analytics v4 synthetic snapshot.

Traffic is generated first, as it would happen. Each scripted incident in
data/scenarios.json is then an event with a cause (a settlement partner outage,
a stale fee table, a lost settlement file), applied to the merchants it reaches
and to the payments those merchants took in the event's window. No payment is
moved or invented for a scenario, so a scenario close has an ordinary volume and
category mix, and its exceptions spread across categories the way the cause
dictates. No row represents a real customer, merchant, payment, or incident.

Distribution choices follow published practice and data: category shares and
ticket sizes calibrated to UK Finance card expenditure statistics, per-category
lognormal amounts and per-entity habits (Sparkov, PaySim, IBM's credit card
generator), heavy-tailed merchant popularity, business-day settlement batches,
refunds linked to a prior purchase, and incidents as clustered anomalies inside
realistic background traffic (AMLworld, ADBench).
"""

from __future__ import annotations

import bisect
import csv
import datetime as dt
import itertools
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from faker import Faker

SEED = 42
NUM_CUSTOMERS = 15_000
NUM_ACCOUNTS = 18_000
NUM_MERCHANTS = 1_500
NUM_TRANSACTIONS = 250_000
NUM_REFUNDS = 9_400
NUM_FRAUD_FLAGS = 7_800
HISTORY_START = dt.date(2016, 1, 1)
START_DATE = dt.date(2022, 1, 1)
END_DATE = dt.date(2024, 12, 31)

DATA_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = DATA_DIR / "raw"
SCENARIO_MANIFEST = DATA_DIR / "scenarios.json"
SETTLEMENT_BATCH_HOUR = 2
DISPUTE_RATE = Decimal("0.0045")
MISMATCH_CONTROLS = 12
EXPECTED_SETTLEMENTS = 200_490

# Every country settles in one of the four supported currencies.
COUNTRY_CURRENCY = {
    "United Kingdom": "GBP", "Canada": "CAD", "Australia": "AUD",
    "Germany": "EUR", "France": "EUR", "Netherlands": "EUR",
    "Spain": "EUR", "Ireland": "EUR", "Italy": "EUR",
}
COUNTRY_WEIGHTS = {
    "United Kingdom": .20, "Canada": .20, "Australia": .20, "Germany": .13,
    "France": .10, "Netherlands": .06, "Spain": .05, "Ireland": .03, "Italy": .03,
}
# category: (median ticket, lognormal sigma, share of purchases, share of
# merchants, refund weight, dispute weight). Purchase shares and medians are
# calibrated to UK Finance card expenditure statistics (Q4 2025): food and
# drink about 38% of card transactions at about GBP 22, entertainment
# (restaurants and pubs) about 22% at about GBP 18, travel about 8% at about
# GBP 37, household goods about 2% at about GBP 84. Medians sit near mean / 1.5.
CATEGORY_PROFILES = {
    "Food & Beverage": (15.0, 0.75, .36, .26, 0.4, 0.5),
    "Entertainment": (14.0, 0.80, .20, .17, 1.2, 1.2),
    "Retail": (30.0, 0.95, .16, .18, 3.0, 1.0),
    "Travel": (45.0, 1.20, .08, .09, 2.0, 2.2),
    "Services": (55.0, 0.95, .07, .12, 1.0, 1.0),
    "Electronics": (90.0, 0.90, .05, .08, 3.0, 2.0),
    "Healthcare": (35.0, 0.85, .05, .06, 0.6, 0.6),
    "Utilities": (60.0, 0.60, .03, .04, 0.2, 0.3),
}
SHARE_BANDS = {
    "Food & Beverage": (.32, .40), "Entertainment": (.17, .23), "Retail": (.13, .19),
    "Travel": (.06, .10), "Services": (.05, .09), "Electronics": (.035, .065),
    "Healthcare": (.03, .065), "Utilities": (.02, .045),
}
MERCHANT_CATEGORIES = list(CATEGORY_PROFILES)
SEGMENT_AMOUNT = {"retail": 1.0, "business": 2.5, "premium": 1.8}
SEGMENT_ACTIVITY = {"retail": 1.0, "business": 1.4, "premium": 1.3}
ACCOUNT_ACTIVITY = {"current": 1.0, "savings": 0.35, "merchant": 0.6}
PURCHASE_SHARE = {"current": .87, "savings": .15, "merchant": 0.0}
RISK_TERMS = {"low": (150, 3), "medium": (250, 3), "high": (400, 5)}
RISK_FAILURE = {"low": 0.0, "medium": 0.4, "high": 0.9}
RISK_FRAUD = {"low": 0.0, "medium": 0.6, "high": 1.4}
RISK_DISPUTE = {"low": 1.0, "medium": 1.8, "high": 3.5}

# Card traffic: quiet overnight, lunchtime and early-evening peaks.
HOUR_WEIGHTS = [
    0.6, 0.35, 0.2, 0.15, 0.15, 0.25, 0.6, 1.2, 2.0, 2.6, 3.0, 3.4,
    4.0, 3.8, 3.4, 3.3, 3.5, 4.0, 4.6, 4.8, 4.2, 3.2, 2.2, 1.2,
]
HOUR_CUMULATIVE = list(itertools.accumulate(HOUR_WEIGHTS))
WEEKDAY_WEIGHTS = [0.95, 0.97, 1.0, 1.02, 1.12, 1.08, 0.86]
MONTH_WEIGHTS = {
    1: .86, 2: .88, 3: .97, 4: .97, 5: 1.0, 6: 1.0,
    7: 1.02, 8: 1.0, 9: .98, 10: 1.02, 11: 1.15, 12: 1.32,
}
ANNUAL_GROWTH = 1.04
MAX_INTENSITY = (
    ANNUAL_GROWTH ** (END_DATE.year - START_DATE.year)
    * max(MONTH_WEIGHTS.values()) * max(WEEKDAY_WEIGHTS)
)
HOLIDAYS = frozenset(
    dt.date(year, month, day)
    for year in range(START_DATE.year, END_DATE.year + 2)
    for month, day in ((1, 1), (12, 25), (12, 26))
)

FRAUD_REASONS = {
    "amount": "Suspicious Amount Spike",
    "cross_border": "High Risk Country Match",
    "velocity": "Velocity Limit Exceeded",
    "new_account": "Mismatched Billing Details",
    "risk": "Card-Not-Present Anomaly",
    "night": "Card-Not-Present Anomaly",
}
TIMESTAMP = "%Y-%m-%d %H:%M:%S"

_fake = Faker()
_customer_end: dict[int, dt.date] = {}
_account_window: dict[int, tuple[dt.date, dt.date]] = {}
_merchant_popularity: dict[int, float] = {}
# scenarioId -> set of merchant ids the incident reaches
_incident_reach: dict[str, set[int]] = {}
# transaction id -> scenarioId whose incident changed its settlement
_incident_hits: dict[int, str] = {}


def reset_seed() -> None:
    """Reset all random sources so repeated calls are byte-stable."""
    global _fake
    random.seed(SEED)
    Faker.seed(SEED)
    _fake = Faker()
    for state in (_customer_end, _account_window, _merchant_popularity, _incident_reach, _incident_hits):
        state.clear()


def _manifest() -> dict[str, Any]:
    return json.loads(SCENARIO_MANIFEST.read_text(encoding="utf-8"))


def _incidents() -> list[dict[str, Any]]:
    """Scenarios that carry an incident, with parsed dates."""
    found = []
    for item in _manifest()["scenarios"]:
        incident = item.get("incident")
        if incident:
            found.append({
                **incident,
                "scenarioId": item["scenarioId"],
                "start": dt.date.fromisoformat(incident["start"]),
                "end": dt.date.fromisoformat(incident["end"]),
            })
    return found


def _write_rows(filename: str, rows: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write empty source table: {filename}")
    destination = OUTPUT_DIR / filename
    temporary = destination.with_suffix(f"{destination.suffix}.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        # csv.DictWriter defaults to CRLF regardless of OS; force LF so the
        # generated bytes match the LF-committed fixtures on every platform.
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(destination)


def _money(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)


def _weighted(options: dict[str, float]) -> str:
    return random.choices(list(options), weights=list(options.values()), k=1)[0]


def _uniform_date(start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=random.randint(0, max((end - start).days, 0)))


def _intensity(day: dt.date) -> float:
    return (
        ANNUAL_GROWTH ** (day.year - START_DATE.year)
        * MONTH_WEIGHTS[day.month]
        * WEEKDAY_WEIGHTS[day.weekday()]
    )


def _seasonal_date(start: dt.date, end: dt.date) -> dt.date:
    """Rejection-sample a day so volume follows growth, season, and weekday."""
    while True:
        day = _uniform_date(start, end)
        if random.random() * MAX_INTENSITY < _intensity(day):
            return day


def _timestamp(day: dt.date) -> dt.datetime:
    hour = random.choices(range(24), cum_weights=HOUR_CUMULATIVE, k=1)[0]
    return dt.datetime.combine(
        day, dt.time(hour, random.randint(0, 59), random.randint(0, 59))
    )


def _parse(value: str) -> dt.datetime:
    return dt.datetime.strptime(value, TIMESTAMP)


def _is_business_day(day: dt.date) -> bool:
    return day.weekday() < 5 and day not in HOLIDAYS


def _add_business_days(day: dt.date, count: int) -> dt.date:
    while count:
        day += dt.timedelta(days=1)
        if _is_business_day(day):
            count -= 1
    return day


def _settlement_day(tx_day: dt.date, sla_days: int) -> dt.date:
    """Next-business-day batches, kept inside the SLA whenever a business day fits."""
    day = _add_business_days(tx_day, random.choices([1, 2, 3], weights=[.72, .23, .05])[0])
    latest = tx_day + dt.timedelta(days=sla_days)
    if day > latest:
        while latest > tx_day and not _is_business_day(latest):
            latest -= dt.timedelta(days=1)
        # A holiday can leave no business day inside the SLA; the batch then
        # runs late on the next business day, as it would in practice.
        day = latest if latest > tx_day else _add_business_days(tx_day, 1)
    return day


def _batch_time(day: dt.date) -> str:
    return dt.datetime.combine(
        day, dt.time(SETTLEMENT_BATCH_HOUR, random.randint(0, 40), random.randint(0, 59))
    ).strftime(TIMESTAMP)


def _top_weighted(items: list[Any], weights: list[float]) -> list[Any]:
    """Order items for weighted sampling without replacement (Efraimidis-Spirakis)."""
    keyed = [
        (random.random() ** (1.0 / weight), index)
        for index, weight in enumerate(weights)
    ]
    keyed.sort(reverse=True)
    return [items[index] for _, index in keyed]


class _Pool:
    """Weighted draw over a fixed list, with cumulative weights built once."""

    def __init__(self, items: list[Any], weights: list[float]) -> None:
        self.items = items
        self.cumulative = list(itertools.accumulate(weights))

    def draw(self) -> Any:
        return self.items[bisect.bisect(self.cumulative, random.random() * self.cumulative[-1])]


def generate_customers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for customer_id in range(1, NUM_CUSTOMERS + 1):
        name = _fake.name()
        country = _weighted(COUNTRY_WEIGHTS)
        # Most customers predate the observed window; the rest join with growth.
        join_date = (
            _uniform_date(HISTORY_START, START_DATE - dt.timedelta(days=1))
            if random.random() < .70
            else _seasonal_date(START_DATE, END_DATE - dt.timedelta(days=30))
        )
        segment = _weighted({"retail": .80, "business": .15, "premium": .05})
        is_active = random.random() < .90
        end = END_DATE
        if not is_active:
            earliest = max(join_date, START_DATE) + dt.timedelta(days=60)
            latest = END_DATE - dt.timedelta(days=180)
            if earliest <= latest:
                end = _uniform_date(earliest, latest)
            else:
                is_active = True
        _customer_end[customer_id] = end
        rows.append({
            "customer_id": customer_id,
            "full_name": name,
            "email": f"{name.lower().replace(' ', '').replace('.', '')}_{customer_id}@example.com",
            "country": country,
            "join_date": join_date.isoformat(),
            "segment": segment,
            "is_active": is_active,
        })
    _write_rows("customers.csv", rows)
    return rows


def generate_accounts(customers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(customer: dict[str, Any], primary: bool) -> None:
        joined = dt.date.fromisoformat(customer["join_date"])
        customer_end = _customer_end[customer["customer_id"]]
        if primary:
            opened = joined + dt.timedelta(days=random.randint(0, 14))
            account_type = _weighted({"current": .92, "savings": .08})
        else:
            opened = _uniform_date(joined, max(joined, customer_end - dt.timedelta(days=30)))
            merchant_share = .25 if customer["segment"] == "business" else .05
            account_type = _weighted({
                "savings": .65 - merchant_share, "current": .35, "merchant": merchant_share,
            })
        home = COUNTRY_CURRENCY[customer["country"]]
        currency = (
            random.choice([code for code in ("EUR", "GBP", "AUD", "CAD") if code != home])
            if random.random() < .08 else home
        )
        status = _weighted({"active": .92, "closed": .05, "suspended": .03})
        end = customer_end
        if status != "active":
            earliest = opened + dt.timedelta(days=60)
            latest = min(customer_end, END_DATE - dt.timedelta(days=30))
            if earliest <= latest:
                end = _uniform_date(earliest, latest)
            else:
                status = "active"
        account_id = len(rows) + 1
        _account_window[account_id] = (max(opened, START_DATE), min(end, END_DATE))
        rows.append({
            "account_id": account_id,
            "customer_id": customer["customer_id"],
            "account_type": account_type,
            "currency": currency,
            "opened_date": opened.isoformat(),
            "status": status,
        })

    for customer in customers:
        add(customer, primary=True)
    while len(rows) < NUM_ACCOUNTS:
        add(random.choice(customers), primary=False)
    _write_rows("accounts.csv", rows)
    return rows


def generate_merchants() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    shares = {name: profile[3] for name, profile in CATEGORY_PROFILES.items()}
    for merchant_id in range(1, NUM_MERCHANTS + 1):
        registered = (
            _uniform_date(HISTORY_START, START_DATE - dt.timedelta(days=1))
            if random.random() < .80
            else _uniform_date(START_DATE, END_DATE - dt.timedelta(days=120))
        )
        rows.append({
            "merchant_id": merchant_id,
            "merchant_name": _fake.company(),
            "category": _weighted(shares),
            "country": _weighted(COUNTRY_WEIGHTS),
            "registration_date": registered.isoformat(),
            "risk_tier": _weighted({"low": .85, "medium": .12, "high": .03}),
        })
        # Pareto popularity gives the usual long tail of small merchants.
        _merchant_popularity[merchant_id] = min(random.paretovariate(0.95), 400.0)
    _write_rows("merchants.csv", rows)
    return rows


def _assign_incident_reach(merchants: list[dict[str, Any]]) -> None:
    """Decide, once per merchant, which incidents reach it.

    Reach is a property of the merchant (its settlement partner, its acquirer,
    whether it joined the repricing campaign), drawn with category weights from
    the manifest. The incident then hits whatever those merchants happen to sell
    in its window, which is what spreads it across categories.
    """
    for incident in _incidents():
        reach = incident["reach"]
        members = set()
        for merchant in merchants:
            registered = dt.date.fromisoformat(merchant["registration_date"])
            if registered > incident["start"]:
                continue
            if random.random() < reach.get(merchant["category"], 0.0):
                members.add(merchant["merchant_id"])
        _incident_reach[incident["scenarioId"]] = members


def _incident_for(tx: dict[str, Any], day: dt.date) -> dict[str, Any] | None:
    """The incident, if any, that changes this completed purchase's settlement."""
    for incident in _incidents():
        if (
            tx["currency"] == incident["currency"]
            and incident["start"] <= day <= incident["end"]
            and tx["merchant_id"] in _incident_reach[incident["scenarioId"]]
        ):
            return incident
    return None


def _purchase_amount(category: str, segment: str) -> Decimal:
    median, sigma = CATEGORY_PROFILES[category][:2]
    value = math.exp(math.log(median * SEGMENT_AMOUNT[segment]) + sigma * random.gauss(0, 1))
    value = min(max(value, 0.50), 25_000.0)
    if random.random() < .10 and value >= 2:
        value = math.floor(value) + random.choice([0.99, 0.0])
    return _money(value)


def _transfer_amount() -> Decimal:
    value = math.exp(math.log(300.0) + 1.1 * random.gauss(0, 1))
    if random.random() < .30:
        step = random.choice([10, 50, 100])
        value = max(step, round(value / step) * step)
    return _money(min(max(value, 1.0), 50_000.0))


def _failure_probability(amount: Decimal, risk_tier: str) -> float:
    logit = -3.3 + 0.35 * math.log(float(amount) / 50.0) + RISK_FAILURE[risk_tier]
    return 1.0 / (1.0 + math.exp(-logit))


def _status(day: dt.date, failure_probability: float) -> str:
    if day >= END_DATE - dt.timedelta(days=2) and random.random() < .55:
        return "pending"
    return "failed" if random.random() < failure_probability else "completed"


def _add_refunds(transactions: list[dict[str, Any]], merchants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merchant_by_id = {row["merchant_id"]: row for row in merchants}
    parents = [
        tx for tx in transactions
        if tx["transaction_type"] == "purchase" and tx["status"] == "completed"
    ]
    weights = [
        CATEGORY_PROFILES[merchant_by_id[tx["merchant_id"]]["category"]][4]
        for tx in parents
    ]
    refunds: list[dict[str, Any]] = []
    for parent in _top_weighted(parents, weights):
        paid_at = _parse(parent["transaction_date"])
        lag = min(45, 1 + int(random.expovariate(1 / 7)))
        day = paid_at.date() + dt.timedelta(days=lag)
        if day > _account_window[parent["account_id"]][1]:
            continue
        amount = parent["amount"] if random.random() < .70 else _money(
            parent["amount"] * Decimal(str(round(random.uniform(.2, .9), 2)))
        )
        if amount <= 0:
            continue
        refunds.append({
            **parent,
            "amount": amount,
            "transaction_date": _timestamp(day).strftime(TIMESTAMP),
            "transaction_type": "refund",
            "status": _status(day, 0.01),
            "_parent": parent,
            "_seq": len(transactions) + len(refunds),
        })
        if len(refunds) == NUM_REFUNDS:
            return refunds
    raise RuntimeError("Not enough refundable purchases")


def generate_transactions(
    customers: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    merchants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    segment_by_customer = {row["customer_id"]: row["segment"] for row in customers}
    # Purchases pick a category at its real-world share first, then a merchant
    # in that category by popularity, preferring the cardholder's own currency.
    domestic: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    anywhere: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for merchant in merchants:
        domestic[(COUNTRY_CURRENCY[merchant["country"]], merchant["category"])].append(merchant)
        anywhere[merchant["category"]].append(merchant)
    popularity = lambda group: [_merchant_popularity[m["merchant_id"]] for m in group]  # noqa: E731
    domestic_pools = {key: _Pool(group, popularity(group)) for key, group in domestic.items()}
    anywhere_pools = {key: _Pool(group, popularity(group)) for key, group in anywhere.items()}
    category_pool = _Pool(MERCHANT_CATEGORIES, [CATEGORY_PROFILES[c][2] for c in MERCHANT_CATEGORIES])

    activity = []
    for account in accounts:
        start, end = _account_window[account["account_id"]]
        days = max((end - start).days + 1, 0)
        activity.append(
            days * random.lognormvariate(0, 0.9) * ACCOUNT_ACTIVITY[account["account_type"]]
            * SEGMENT_ACTIVITY[segment_by_customer[account["customer_id"]]]
        )
    account_pool = _Pool(accounts, activity)

    rows: list[dict[str, Any]] = []
    for _ in range(NUM_TRANSACTIONS - NUM_REFUNDS):
        account = account_pool.draw()
        start, end = _account_window[account["account_id"]]
        segment = segment_by_customer[account["customer_id"]]
        merchant = None
        if random.random() < PURCHASE_SHARE[account["account_type"]]:
            category = category_pool.draw()
            for _attempt in range(5):
                pool = domestic_pools.get((account["currency"], category))
                pick = (pool if pool and random.random() < .85 else anywhere_pools[category]).draw()
                if dt.date.fromisoformat(pick["registration_date"]) <= end:
                    merchant = pick
                    break
        if merchant is None:
            day = _seasonal_date(start, end)
            amount = _transfer_amount()
            status = _status(day, 0.02)
            tx_type, merchant_id = "transfer", ""
        else:
            registered = dt.date.fromisoformat(merchant["registration_date"])
            day = _seasonal_date(max(start, registered), end)
            amount = _purchase_amount(merchant["category"], segment)
            status = _status(day, _failure_probability(amount, merchant["risk_tier"]))
            tx_type, merchant_id = "purchase", merchant["merchant_id"]
        rows.append({
            "account_id": account["account_id"],
            "merchant_id": merchant_id,
            "amount": amount,
            "currency": account["currency"],
            "transaction_date": _timestamp(day).strftime(TIMESTAMP),
            "transaction_type": tx_type,
            "status": status,
            "_parent": None,
            "_seq": len(rows),
        })

    rows.extend(_add_refunds(rows, merchants))

    # Ledger IDs increase with time, as they would in a real payments system.
    rows.sort(key=lambda tx: (tx["transaction_date"], tx["_seq"]))
    for transaction_id, tx in enumerate(rows, start=1):
        tx["transaction_id"] = transaction_id

    output = [
        {
            "transaction_id": tx["transaction_id"],
            "account_id": tx["account_id"],
            "merchant_id": tx["merchant_id"],
            "amount": f"{tx['amount']:.2f}",
            "currency": tx["currency"],
            "transaction_date": tx["transaction_date"],
            "transaction_type": tx["transaction_type"],
            "status": tx["status"],
            "parent_transaction_id": tx["_parent"]["transaction_id"] if tx["_parent"] else "",
        }
        for tx in rows
    ]
    _write_rows("transactions.csv", output)
    return output


def generate_merchant_terms(merchants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Base terms by risk tier; repriced merchants get a second, cheaper term."""
    repricing = next((i for i in _incidents() if i["type"] == "stale_fee_schedule"), None)
    repriced = _incident_reach.get(repricing["scenarioId"], set()) if repricing else set()
    rows: list[dict[str, Any]] = []
    for merchant in merchants:
        fee_bps, sla_days = RISK_TERMS[merchant["risk_tier"]]
        common = {
            "merchant_id": merchant["merchant_id"],
            "valid_from": merchant["registration_date"],
            "fee_rate_bps": fee_bps,
            "settlement_sla_days": sla_days,
        }
        if merchant["merchant_id"] in repriced:
            rows.append({**common, "valid_to": (repricing["start"] - dt.timedelta(days=1)).isoformat()})
            rows.append({
                **common,
                "valid_from": repricing["start"].isoformat(),
                "valid_to": "",
                "fee_rate_bps": fee_bps - int(repricing["feeCutBps"]),
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
    tx_by_id = {row["transaction_id"]: row for row in transactions}

    rows: list[dict[str, Any]] = []
    for tx in transactions:
        if tx["status"] != "completed" or tx["merchant_id"] == "":
            continue
        tx_id = tx["transaction_id"]
        tx_day = _parse(tx["transaction_date"]).date()
        term = _effective_term(terms_by_merchant, tx["merchant_id"], tx_day)
        sla_days = int(term["settlement_sla_days"])
        gross = _money(tx["amount"])
        status = "settled"
        if tx["transaction_type"] == "refund":
            # Refunds are debited from the merchant's next payout, with no fee.
            fee, settled = Decimal("0.00"), -gross
            settle_day = _settlement_day(tx_day, sla_days)
        else:
            incident = _incident_for(tx, tx_day)
            if incident:
                _incident_hits[tx_id] = incident["scenarioId"]
            if incident and incident["type"] == "lost_settlement_file":
                continue
            applied_bps = int(term["fee_rate_bps"])
            if incident and incident["type"] == "stale_fee_schedule":
                applied_bps += int(incident["feeCutBps"])
            fee = _money(gross * Decimal(applied_bps) / Decimal(10_000))
            settled = gross - fee
            if incident and incident["type"] == "partner_outage":
                settle_day = tx_day + dt.timedelta(days=sla_days + 3)
                status = "delayed"
            else:
                settle_day = _settlement_day(tx_day, sla_days)
        rows.append({
            "transaction_id": tx_id,
            "settlement_date": _batch_time(settle_day),
            "currency": tx["currency"],
            "settled_amount": f"{settled:.2f}",
            "processing_fee": f"{fee:.2f}",
            "status": status,
            "_type": tx["transaction_type"],
        })

    # Background disputes and data errors land on any day, scenario closes
    # included, at their usual rate. They skip payments an incident already
    # changed so each scenario's count stays attributable to its cause.
    open_purchases = [
        row for row in rows
        if row["_type"] == "purchase" and row["transaction_id"] not in _incident_hits
    ]
    weights = []
    for row in open_purchases:
        tx = tx_by_id[row["transaction_id"]]
        merchant = merchant_by_id[tx["merchant_id"]]
        weights.append(
            CATEGORY_PROFILES[merchant["category"]][5]
            * RISK_DISPUTE[merchant["risk_tier"]]
            * math.log1p(float(tx["amount"]))
        )
    ranked = _top_weighted(open_purchases, weights)
    disputes = int((Decimal(len(open_purchases)) * DISPUTE_RATE).to_integral_value(ROUND_HALF_UP))
    for row in ranked[:disputes]:
        row["status"] = "disputed"

    controls = ranked[disputes:disputes + MISMATCH_CONTROLS]
    currency_cycle = {"EUR": "GBP", "GBP": "EUR", "AUD": "CAD", "CAD": "AUD"}
    for row in controls[: MISMATCH_CONTROLS // 2]:
        row["currency"] = currency_cycle[row["currency"]]
    for row in controls[MISMATCH_CONTROLS // 2:]:
        row["settled_amount"] = f"{_money(row['settled_amount']) - Decimal('0.25'):.2f}"

    rows.sort(key=lambda row: (row["settlement_date"], row["transaction_id"]))
    output = [
        {
            "settlement_id": settlement_id,
            "transaction_id": row["transaction_id"],
            "settlement_date": row["settlement_date"],
            "currency": row["currency"],
            "settled_amount": row["settled_amount"],
            "processing_fee": row["processing_fee"],
            "status": row["status"],
        }
        for settlement_id, row in enumerate(rows, start=1)
    ]
    _write_rows("settlements.csv", output)
    return output


def generate_fraud_flags(
    transactions: list[dict[str, Any]],
    accounts: list[dict[str, Any]],
    merchants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    account_by_id = {row["account_id"]: row for row in accounts}
    merchant_by_id = {row["merchant_id"]: row for row in merchants}
    amounts: dict[int, list[float]] = {}
    daily: Counter[tuple[int, str]] = Counter()
    for tx in transactions:
        amounts.setdefault(tx["account_id"], []).append(float(tx["amount"]))
        daily[(tx["account_id"], tx["transaction_date"][:10])] += 1
    typical = {account_id: statistics.median(values) for account_id, values in amounts.items()}

    scored = []
    for tx in transactions:
        if tx["status"] == "failed" or tx["transaction_type"] == "refund":
            continue
        account = account_by_id[tx["account_id"]]
        when = _parse(tx["transaction_date"])
        merchant = merchant_by_id.get(tx["merchant_id"]) if tx["merchant_id"] != "" else None
        components = {
            "amount": 1.2 * max(0.0, math.log(float(tx["amount"]) / typical[tx["account_id"]])),
            "risk": RISK_FRAUD[merchant["risk_tier"]] if merchant else 0.0,
            "cross_border": 0.9 if merchant and COUNTRY_CURRENCY[merchant["country"]] != account["currency"] else 0.0,
            "night": 0.7 if when.hour < 5 else 0.0,
            "new_account": 0.6 if (when.date() - dt.date.fromisoformat(account["opened_date"])).days < 30 else 0.0,
            "velocity": 0.8 if daily[(tx["account_id"], tx["transaction_date"][:10])] >= 4 else 0.0,
        }
        score = sum(components.values()) + random.gauss(0, 0.35)
        scored.append((score, tx["transaction_id"], tx, max(components, key=components.get)))
    scored.sort(key=lambda item: (-item[0], item[1]))

    flags = []
    for _, _, tx, driver in scored[:NUM_FRAUD_FLAGS]:
        flagged = _parse(tx["transaction_date"]) + dt.timedelta(minutes=random.randint(1, 180))
        recent = flagged.date() > END_DATE - dt.timedelta(days=21)
        unresolved = random.random() < (.85 if recent else .03)
        resolved = flagged + dt.timedelta(
            days=min(30, 1 + int(random.expovariate(1 / 3))), hours=random.randint(0, 8)
        )
        flags.append({
            "transaction_id": tx["transaction_id"],
            "flagged_date": flagged.strftime(TIMESTAMP),
            "flag_reason": FRAUD_REASONS[driver],
            "is_resolved": not unresolved,
            "resolved_date": "" if unresolved else resolved.strftime(TIMESTAMP),
        })
    flags.sort(key=lambda row: (row["flagged_date"], row["transaction_id"]))
    rows = [{"flag_id": index, **row} for index, row in enumerate(flags, start=1)]
    _write_rows("fraud_flags.csv", rows)
    return rows


def _benford_mad(amounts: list[str]) -> float:
    digits = Counter(str(int(Decimal(value) * 100))[0] for value in amounts)
    total = sum(digits.values())
    return sum(
        abs(digits[str(d)] / total - math.log10(1 + 1 / d)) for d in range(1, 10)
    ) / 9


def scenario_report(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """What each scenario close looks like: volume, and how the incident spreads."""
    merchant_category = {row["merchant_id"]: row["category"] for row in tables["merchants"]}
    eligible_by_close: Counter[tuple[str, str]] = Counter()
    for tx in tables["transactions"]:
        if tx["transaction_type"] == "purchase" and tx["status"] == "completed":
            eligible_by_close[(tx["transaction_date"][:10], tx["currency"])] += 1
    report = {}
    tx_by_id = {row["transaction_id"]: row for row in tables["transactions"]}
    for item in _manifest()["scenarios"]:
        close, currency = item["closeDate"], item["defaultCurrency"]
        # Compared with the same month, so a busy December day is judged
        # against other December days.
        days = sorted(
            count for (day, code), count in eligible_by_close.items()
            if code == currency and day[:7] == close[:7]
        )
        hits = Counter(
            merchant_category[tx_by_id[tx_id]["merchant_id"]]
            for tx_id, scenario_id in _incident_hits.items()
            if scenario_id == item["scenarioId"]
            and tx_by_id[tx_id]["transaction_date"][:10] == close
            and tx_by_id[tx_id]["currency"] == currency
        )
        total = sum(hits.values())
        top = hits.most_common(1)[0] if hits else (None, 0)
        report[item["scenarioId"]] = {
            "eligible_on_close": eligible_by_close[(close, currency)],
            "median_day": statistics.median(days),
            "affected": total,
            "dominant": top[0],
            "dominant_share": round(top[1] / total, 3) if total else 0.0,
            "categories_hit": len(hits),
            "by_category": dict(hits.most_common()),
        }
    return report


def realism_report(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Measure the targets this generator is designed to hit."""
    transactions = tables["transactions"]
    tx_by_id = {row["transaction_id"]: row for row in transactions}
    merchant_category = {row["merchant_id"]: row["category"] for row in tables["merchants"]}
    eligible = [
        tx for tx in transactions
        if tx["transaction_type"] == "purchase" and tx["status"] == "completed"
    ]
    years = Counter(tx["transaction_date"][:4] for tx in transactions)
    by_merchant = Counter(tx["merchant_id"] for tx in eligible)
    top = sorted(by_merchant.values(), reverse=True)[: max(1, len(by_merchant) // 10)]
    categories = Counter(merchant_category[tx["merchant_id"]] for tx in eligible)
    currencies = sorted({tx["currency"] for tx in eligible})
    refunds = [tx for tx in transactions if tx["transaction_type"] == "refund"]
    return {
        "year_share": {
            year: round(count / len(transactions), 3) for year, count in sorted(years.items())
        },
        "category_share": {
            name: round(categories[name] / len(eligible), 3) for name in MERCHANT_CATEGORIES
        },
        "benford_mad": {
            code: round(_benford_mad([tx["amount"] for tx in eligible if tx["currency"] == code]), 4)
            for code in currencies
        },
        "top_decile_merchant_share": round(sum(top) / len(eligible), 3),
        "orphan_refunds": sum(
            1 for tx in refunds
            if not tx["parent_transaction_id"]
            or tx_by_id[tx["parent_transaction_id"]]["transaction_type"] != "purchase"
            or tx_by_id[tx["parent_transaction_id"]]["status"] != "completed"
            or tx_by_id[tx["parent_transaction_id"]]["account_id"] != tx["account_id"]
            or tx_by_id[tx["parent_transaction_id"]]["merchant_id"] != tx["merchant_id"]
            or tx_by_id[tx["parent_transaction_id"]]["transaction_date"] >= tx["transaction_date"]
        ),
        "weekend_settlements": sum(
            1 for row in tables["settlements"]
            if row["status"] != "delayed" and _parse(row["settlement_date"]).weekday() >= 5
        ),
        "transactions_outside_account_window": sum(
            1 for tx in transactions
            if not (
                _account_window[tx["account_id"]][0]
                <= _parse(tx["transaction_date"]).date()
                <= _account_window[tx["account_id"]][1]
            )
        ),
        "fraud_flags_on_failed": sum(
            1 for flag in tables["fraud_flags"]
            if tx_by_id[flag["transaction_id"]]["status"] == "failed"
        ),
        "dispute_rate": round(
            sum(row["status"] == "disputed" for row in tables["settlements"]) / len(eligible), 4
        ),
        "scenarios": scenario_report(tables),
    }


def validate_generated_snapshot(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    expected = {
        "customers": NUM_CUSTOMERS, "accounts": NUM_ACCOUNTS,
        "merchants": NUM_MERCHANTS, "transactions": NUM_TRANSACTIONS,
        "settlements": EXPECTED_SETTLEMENTS, "fraud_flags": NUM_FRAUD_FLAGS,
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

    report = realism_report(tables)
    problems = []
    if not all(.25 <= share <= .42 for share in report["year_share"].values()):
        problems.append("year_share")
    for name, (low, high) in SHARE_BANDS.items():
        if not low <= report["category_share"][name] <= high:
            problems.append(f"category_share:{name}")
    if any(mad > 0.012 for mad in report["benford_mad"].values()):
        problems.append("benford_mad")
    if report["top_decile_merchant_share"] < .40:
        problems.append("top_decile_merchant_share")
    for key in (
        "orphan_refunds", "weekend_settlements",
        "transactions_outside_account_window", "fraud_flags_on_failed",
    ):
        if report[key]:
            problems.append(key)
    if not report["dispute_rate"] < .009:
        problems.append("dispute_rate")

    # Scenario closes must look like ordinary days hit by a cause, not batches.
    for item in _manifest()["scenarios"]:
        found = report["scenarios"][item["scenarioId"]]
        if not .6 <= found["eligible_on_close"] / found["median_day"] <= 1.6:
            problems.append(f"{item['scenarioId']}:volume")
        if found["affected"] != int(item["expectedSignal"]["affectedPayments"]):
            problems.append(f"{item['scenarioId']}:affectedPayments={found['affected']}")
        if item.get("incident"):
            if found["dominant"] != item["focusCategory"]:
                problems.append(f"{item['scenarioId']}:focusCategory={found['dominant']}")
            if not .3 <= found["dominant_share"] <= .7 or found["categories_hit"] < 3:
                problems.append(f"{item['scenarioId']}:spread")
    if problems:
        raise RuntimeError(f"Realism targets missed ({', '.join(problems)}): {json.dumps(report, indent=1)}")
    return report


def main() -> None:
    reset_seed()
    customers = generate_customers()
    accounts = generate_accounts(customers)
    merchants = generate_merchants()
    _assign_incident_reach(merchants)
    transactions = generate_transactions(customers, accounts, merchants)
    merchant_terms = generate_merchant_terms(merchants)
    settlements = generate_settlements(transactions, merchants, merchant_terms)
    fraud_flags = generate_fraud_flags(transactions, accounts, merchants)
    report = validate_generated_snapshot({
        "customers": customers, "accounts": accounts, "merchants": merchants,
        "merchant_terms": merchant_terms, "transactions": transactions,
        "settlements": settlements, "fraud_flags": fraud_flags,
    })
    print(
        f"Generated deterministic synthetic snapshot {_manifest()['datasetVersion']} "
        f"in {OUTPUT_DIR}"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
