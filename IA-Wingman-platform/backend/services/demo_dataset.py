"""A fixed synthetic onboarding/payments dataset for the fieldwork agents' demo.
Deterministic (no randomness) with a handful of deliberately planted anomalies
so the Data-Analysis checks always surface known exceptions:

  - a duplicate customer (CUST200 on two cases)
  - 3 cases missing beneficial-ownership evidence
  - 2 segregation-of-duties conflicts (maker == checker)
  - 3 amounts just below the 10,000 approval threshold (possible gaming)
  - 1 clear amount outlier

Each row also carries synthetic personal data (name, email, IBAN, phone, BSN) so
the Privacy Guard agent has real PII to detect, classify and mask. All of it is
fabricated — no real people or organisations. The Data-Analysis engine keys only
off case_id/customer_id/amount/ubo_verified/maker/checker, so the extra columns
are inert for it; the analysis is unchanged.

Later phases can swap this for a CSV/Excel upload; both engines are agnostic to
where the rows come from.
"""

_MAKERS = ["a.jansen", "b.devries", "c.smit", "d.bakker"]
_CHECKERS = ["e.mulder", "f.visser", "g.meijer", "h.bos"]
_COUNTRIES = ["NL", "BE", "DE", "FR"]
_RATINGS = ["low", "medium", "high"]

# Fabricated names for the synthetic customers (no real individuals).
_NAMES = [
    "Hans Mueller", "Sofia Rossi", "Liam O'Brien", "Emma Janssen", "Noah Dubois",
    "Olivia Nowak", "Lucas Andersson", "Mia Fernandez", "Daan Visser", "Ava Kowalski",
    "Finn Larsen", "Isla Moreau", "Sem Bakker", "Ella Novak", "Luca Bianchi",
    "Nora Haugen", "Tom Vermeulen", "Zoe Lambert", "Jesse de Wit", "Lena Vogel",
]


def _make_bsn(seed: int) -> str:
    """Deterministic, valid Dutch BSN (passes the 11-proef).

    Builds an 8-digit prefix from the seed and computes the 9th check digit so
    the detector's checksum validation accepts it.
    """
    weights = [9, 8, 7, 6, 5, 4, 3, 2]
    prefix = 10_000_000 + (seed * 1_234_567) % 90_000_000
    for _ in range(11):  # nudge the prefix until the check digit is 0-9
        s = f"{prefix:08d}"
        d9 = sum(int(c) * w for c, w in zip(s, weights)) % 11
        if d9 != 10:
            return s + str(d9)
        prefix += 1
    return f"{prefix:08d}0"


def demo_dataset() -> list[dict]:
    rows = []
    for i in range(20):
        name = _NAMES[i]
        first, _, last = name.partition(" ")
        rows.append({
            "case_id": f"C{1000 + i}",
            "customer_id": f"CUST{200 + i}",       # unique by default
            "customer_name": name,
            "email": f"{first}.{last}@example.com".lower().replace("'", ""),
            "iban": f"NL{(20 + i) % 100:02d}INGB{i:010d}",
            "phone": f"+31 6 {10_000_000 + i * 111_111:08d}",
            "bsn": _make_bsn(i),                    # national id — excessive for the audit
            "amount": 1000 + i * 137,               # spread 1000–3603, none near the threshold
            "ubo_verified": "yes",
            "maker": _MAKERS[i % 4],
            "checker": _CHECKERS[i % 4],            # maker != checker by default
            "country": _COUNTRIES[i % 4],
            "risk_rating": _RATINGS[i % 3],
        })

    # Planted anomalies (known counts for a predictable demo):
    rows[5]["customer_id"] = "CUST200"              # duplicate of rows[0] → 2 rows
    for idx in (2, 7, 11):                          # missing UBO evidence → 3 rows
        rows[idx]["ubo_verified"] = ""
    rows[3]["checker"] = rows[3]["maker"]           # SoD conflict → 2 rows
    rows[9]["checker"] = rows[9]["maker"]
    rows[4]["amount"] = 9800                        # threshold gaming (< 10,000) → 3 rows
    rows[8]["amount"] = 9950
    rows[12]["amount"] = 9600
    rows[15]["amount"] = 480000                     # clear outlier → 1 row
    return rows
