import re
import json

def parse_statement(text):
    # Remove all spaces and newlines
    compact = text.replace(' ', '').replace('\n', '')
    
    # Regex:
    # 1. Date: (\d{2}-\d{2}-\d{2})
    # 2. Desc: ((?:(?!\d{2}-\d{2}-\d{2}).)*?)
    # 3. Credit/Debit and Balance:
    # We look for either (Credit)0 or 0(Debit) followed by Balance.
    # Both Credit and Debit are \d+\.\d{2}
    pattern = r'(\d{2}-\d{2}-\d{2})((?:(?!\d{2}-\d{2}-\d{2}).)*?)-?(?:(\d+\.\d{2})0|0(\d+\.\d{2}))(\d+\.\d{2})'
    
    matches = re.findall(pattern, compact)
    
    results = []
    for m in matches:
        date, desc, credit, debit, balance = m
        
        # Additional filter to ensure it's a valid transaction:
        # Desc shouldn't be insanely long and shouldn't contain header keywords
        if len(desc) > 100 or 'TRANSACTIONACCOUNTS' in desc or 'AVAILABLEBALANCE' in desc.upper():
            continue
            
        results.append({
            "date": date,
            "desc": desc,
            "credit": float(credit) if credit else 0.0,
            "debit": float(debit) if debit else 0.0,
            "balance": float(balance)
        })
        
    return results

if __name__ == '__main__':
    with open('sample_text.txt', 'r') as f:
        text = f.read()
    
    transactions = parse_statement(text)
    
    print(f"Extracted {len(transactions)} valid transactions:")
    for t in transactions[:3]:
        print(t)
    print("...")
    for t in transactions[-3:]:
        print(t)
