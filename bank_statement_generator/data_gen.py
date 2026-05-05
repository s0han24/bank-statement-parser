import calendar
from datetime import date
from typing import Optional

NAMES = [
    "Rahul Sharma", "Priya Mehta", "Amit Verma", "Sneha Iyer", "Karan Patel",
    "Ananya Singh", "Rohit Gupta", "Divya Nair", "Suresh Kumar", "Pooja Joshi",
    "Arjun Reddy", "Meera Pillai", "Vikram Malhotra", "Nisha Agarwal", "Sanjay Bose",
    "Kavya Krishnan", "Deepak Tiwari", "Ritu Saxena", "Manish Dubey", "Swati Bhatt",
]
MERCHANTS_FOOD  = ["Swiggy", "Zomato", "McDonalds", "Dominos", "Haldirams",
                   "Cafe Coffee Day", "Blinkit", "BigBasket", "Natures Basket", "D-Mart"]
MERCHANTS_SHOP  = ["Amazon", "Flipkart", "Myntra", "Ajio", "Nykaa",
                   "Tata CLiQ", "Reliance Digital", "Croma", "Lifestyle", "Snapdeal"]
MERCHANTS_UTIL  = ["Airtel", "Jio", "BSES Rajdhani", "Tata Power", "MahaVitaran",
                   "MSEDCL", "Paytm Fastag", "IRCTC", "BookMyShow", "MakeMyTrip"]
MERCHANTS_LOCAL = ["Kirana Store", "Medical Plus", "Petrol Pump", "Chemist World",
                   "Aggarwal Sweets", "Vijay Sales", "Local Bakery", "Corner Shop"]
CITIES          = ["Mumbai", "Delhi", "Bangalore", "Pune", "Hyderabad",
                   "Chennai", "Kolkata", "Ahmedabad", "Jaipur", "Noida"]
BANKS_NEFT      = ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank",
                   "Kotak Mahindra Bank", "Yes Bank", "IndusInd Bank"]
EMPLOYERS       = ["Infosys Ltd", "TCS", "Wipro Ltd", "HCL Technologies",
                   "Cognizant", "Accenture India", "Tech Mahindra", "IBM India"]
BANK_NAMES      = ["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Mahindra Bank"]

class SeededRNG:
    """Park-Miller LCG — reproducible, portable."""
    def __init__(self, seed: int):
        self.s = seed % 2147483647 or 1

    def next(self) -> float:
        self.s = (self.s * 16807) % 2147483647
        return (self.s - 1) / 2147483646

    def pick(self, arr):
        return arr[int(self.next() * len(arr))]

    def weighted(self, items, weights):
        total = sum(weights)
        r = self.next() * total
        for item, w in zip(items, weights):
            r -= w
            if r <= 0:
                return item
        return items[-1]

    def skew(self, lo, hi, power=2.0):
        """Power-law skewed sample — biased toward lo."""
        return round((lo + (hi - lo) * (self.next() ** power)) * 100) / 100

    def txn_id(self, length=12):
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(chars[int(self.next() * len(chars))] for _ in range(length))

def _generate_description(rng: SeededRNG, txn_type: str) -> str:
    upper = rng.next() > 0.5
    city  = rng.pick(CITIES)

    def fmt(s): return s.upper() if upper else s
    bank_short = rng.pick(["HDFC", "ICIC", "SBIN", "UTIB", "KKBK", "YESB", "PAYT"])

    if txn_type == "salary":
        emp = rng.pick(EMPLOYERS).replace(" ", "")
        return fmt(f"NEFT*{bank_short}*{rng.txn_id(10)}*{emp}")

    if txn_type == "freelance_credit":
        client = rng.pick(["Upwork", "Fiverr", "Toptal", "Freelancer"]).upper()
        return fmt(f"NEFT*{bank_short}*{rng.txn_id(10)}*{client}")

    if txn_type == "upi_debit":
        m = rng.pick(MERCHANTS_FOOD if rng.next() > 0.5 else MERCHANTS_SHOP).replace(" ", "").upper()
        vpa = f"{m.lower()}@upi"
        return fmt(f"UPI/DR/{rng.txn_id(12)}/{m}/{bank_short}/{vpa}/UPI")

    if txn_type == "upi_credit":
        name = rng.pick(NAMES).replace(" ", "").upper()
        vpa = f"{name.lower()}@upi"
        return fmt(f"UPI/CR/{rng.txn_id(12)}/{name}/{bank_short}/{vpa}/UPI")

    if txn_type == "pos_debit":
        m = rng.pick(MERCHANTS_SHOP if rng.next() > 0.5 else MERCHANTS_LOCAL).replace(" ", "").upper()
        return fmt(f"POS/{m}")

    if txn_type == "atm":
        return fmt(f"ATM WDL/{city.upper()}/{rng.txn_id(8)}")

    if txn_type == "bill":
        util = rng.pick(MERCHANTS_UTIL).replace(" ", "").upper()
        return fmt(f"UPI/DR/{rng.txn_id(12)}/{util}/{bank_short}/billpay@upi/UPI")

    if txn_type == "refund":
        m = rng.pick(MERCHANTS_SHOP + MERCHANTS_FOOD).replace(" ", "").upper()
        return fmt(f"NEFT*{bank_short}*{rng.txn_id(10)}*REFUND{m}")

    if txn_type == "interest":
        return fmt("INTEREST CREDIT")

    if txn_type == "charge":
        opts = ["ANNUAL MAINT CHARGE", "SMS ALERT CHARGES", "DEBIT CARD FEE"]
        return fmt(rng.pick(opts))

    if txn_type == "reversal":
        method = rng.pick(["UPI", "NEFT", "IMPS"])
        return fmt(f"REVERSAL/{method}/{rng.txn_id(10)}")

    if txn_type == "neft_in":
        name = rng.pick(NAMES).replace(" ", "").upper()
        return fmt(f"NEFT*{bank_short}*{rng.txn_id(10)}*{name}")

    if txn_type == "long_desc":
        bank  = rng.pick(BANKS_NEFT).replace(" ", "-").upper()
        name  = rng.pick(NAMES).replace(" ", "-").upper()
        ifsc  = rng.pick(["HDFC", "ICIC", "SBIN"]) + f"0{int(rng.next()*99999):05d}"
        return f"AUTOMATED-CLEARING-HOUSE-PAYMENT-REF-{rng.txn_id()}-FROM-{name}-VIA-{bank}-IFSC-{ifsc}"

    return fmt(f"UPI/DR/{rng.txn_id(12)}/UNKNOWN/{bank_short}/unknown@upi/UPI")

def _sample_amount(rng: SeededRNG, txn_type: str, persona: str) -> float:
    if txn_type == "salary":
        bases = {"salaried": 65000, "freelance": 0, "highspend": 120000, "lowspend": 40000}
        return round((bases.get(persona, 65000)) * (0.9 + rng.next() * 0.2))
    if txn_type == "freelance_credit": return rng.skew(8000,  80000, 1.5)
    if txn_type in ["upi_debit", "upi_credit"]: return rng.skew(50, 3000, 2.5)
    if txn_type == "pos_debit":        return rng.skew(200,   8000,  2.0)
    if txn_type == "atm":              return round(rng.skew(1000, 15000, 1.5) / 500) * 500
    if txn_type == "bill":             return rng.skew(200,   5000,  1.8)
    if txn_type == "refund":           return rng.skew(50,    3000,  2.0)
    if txn_type == "interest":         return rng.skew(10,    200,   3.0)
    if txn_type == "charge":           return rng.skew(50,    600,   1.2)
    if txn_type == "reversal":         return rng.skew(50,    3000,  2.0)
    if txn_type == "neft_in":          return rng.skew(500,   20000, 1.5)
    if txn_type == "zero":             return 0.0
    return rng.skew(100, 2000, 2.0)

DEBIT_TYPES   = ["upi_debit", "pos_debit", "atm", "bill"]
DEBIT_WEIGHTS = [60, 15, 8, 7]
CREDIT_TYPES  = {"salaried": ["salary",          "neft_in", "refund", "interest", "upi_credit"],
                 "freelance": ["freelance_credit", "neft_in", "refund", "interest", "upi_credit"],
                 "highspend": ["salary",           "neft_in", "refund", "interest", "upi_credit"],
                 "lowspend":  ["salary",           "neft_in", "refund", "interest", "upi_credit"]}
CREDIT_WEIGHTS = {"salaried":  [40, 20, 10, 10, 20],
                  "freelance": [30, 30, 10, 10, 20],
                  "highspend": [40, 20, 10, 10, 20],
                  "lowspend":  [40, 20, 10, 10, 20]}
CREDIT_IS_CREDIT = {"salary", "freelance_credit", "neft_in", "interest", "refund", "reversal", "upi_credit"}
DEBIT_IS_DEBIT   = {"upi_debit", "pos_debit", "atm", "bill", "charge"}
EDGE_TYPES       = ["zero", "long_desc", "reversal", "charge"]

def generate_statement(
    bank_name: str,
    month_str: str,       # "YYYY-MM"
    init_balance: float,
    tx_count: int,
    debit_ratio: float,   # 0.0-1.0
    edge_density: float,  # 0.0-1.0
    persona: str,
    allow_overdraft: bool,
    seed: int,
) -> dict:
    rng = SeededRNG(seed)
    year, month = map(int, month_str.split("-"))
    days_in_month = calendar.monthrange(year, month)[1]

    name   = rng.pick(NAMES)
    ac_num = f"XXXX XXXX XXXX {int(rng.next()*9000+1000)}"
    ifsc   = rng.pick(["HDFC", "ICIC", "SBIN", "UTIB", "KKBK"]) + f"0{int(rng.next()*99999):05d}"
    branch = rng.pick(CITIES) + " Main Branch"

    balance     = round(init_balance * (0.85 + rng.next() * 0.3), 2)
    opening_bal = balance
    target_tx   = tx_count + int(rng.next() * 10 - 5)
    salary_done = False
    current_day = 1
    txns        = []

    ct = CREDIT_TYPES.get(persona, CREDIT_TYPES["salaried"])
    cw = CREDIT_WEIGHTS.get(persona, CREDIT_WEIGHTS["salaried"])

    for _ in range(max(target_tx, 1)):
        current_day += int(rng.next() * 3)
        current_day  = min(current_day, days_in_month)

        if rng.next() < edge_density:
            txn_type = rng.pick(EDGE_TYPES)
            is_credit = txn_type in CREDIT_IS_CREDIT or rng.next() > 0.6
        elif persona == "salaried" and not salary_done and current_day <= 7:
            txn_type  = "salary"
            is_credit = True
            salary_done = True
        else:
            is_credit = rng.next() > debit_ratio
            txn_type  = rng.weighted(ct, cw) if is_credit else rng.weighted(DEBIT_TYPES, DEBIT_WEIGHTS)

        if txn_type in CREDIT_IS_CREDIT: is_credit = True
        if txn_type in DEBIT_IS_DEBIT:   is_credit = False

        amount = _sample_amount(rng, txn_type, persona)
        if not allow_overdraft and not is_credit and balance - amount < -100:
            amount = max(0.0, balance * 0.3)
        amount = round(amount, 2)

        balance = round(balance + (amount if is_credit else -amount), 2)
        txns.append({
            "date":        f"{year}-{month:02d}-{current_day:02d}",
            "description": _generate_description(rng, txn_type),
            "debit":       None if is_credit else amount,
            "credit":      amount if is_credit else None,
            "balance":     balance,
        })

    return {
        "account_holder":  name,
        "account_number":  ac_num,
        "ifsc_code":       ifsc,
        "branch":          branch,
        "bank_name":       bank_name,
        "statement_period": [f"{year}-{month:02d}-01", f"{year}-{month:02d}-{days_in_month:02d}"],
        "opening_balance": opening_bal,
        "closing_balance": balance,
        "transactions":    txns,
    }
