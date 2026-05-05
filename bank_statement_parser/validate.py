import pandas as pd
import argparse

def validate_dataframe(df):
    if df.empty:
        return {"error": "The statement is empty."}
        
    required_columns = {'amount', 'type', 'balance'}
    if not required_columns.issubset(df.columns):
        return {"error": f"Missing required columns. Need {required_columns}."}

    total_checks = 0
    passed_checks = 0
    failed_rows = []
    
    previous_balance = None

    for index, row in df.iterrows():
        current_balance = row.get('balance')
        if pd.notna(current_balance):
            current_balance = float(current_balance)
            if previous_balance is not None:
                total_checks += 1
                
                amount = float(row.get('amount', 0.0))
                tx_type = str(row.get('type', '')).lower().strip()
                
                expected_balance = previous_balance + amount if tx_type == 'credit' else previous_balance - amount
                
                if abs(current_balance - expected_balance) < 0.01:
                    passed_checks += 1
                else:
                    failed_rows.append({
                        "index": index,
                        "prev_bal": previous_balance,
                        "amount": amount,
                        "type": tx_type,
                        "expected": expected_balance,
                        "actual": current_balance
                    })
            
            if current_balance != 0.0 or (previous_balance is not None and abs(current_balance - expected_balance) < 0.01):
                previous_balance = current_balance
            else:
                previous_balance = None
        else:
            previous_balance = None

    result = {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_rows": failed_rows
    }
    if total_checks > 0:
        result["pass_percentage"] = (passed_checks / total_checks) * 100
        
    return result

def validate_statement(file_path):
    try:
        if file_path.lower().endswith('.json'):
            df = pd.read_json(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return
        
    res = validate_dataframe(df)
    if "error" in res:
        print(res["error"])
        return
        
    if res["total_checks"] > 0:
        for f in res["failed_rows"]:
            print(f"Row {f['index']} failed: Prev {f['prev_bal']:.2f}, Amount {f['amount']:.2f} ({f['type']}), Expected {f['expected']:.2f}, Actual {f['actual']:.2f}")
            
        print("\n--- Validation Summary ---")
        print(f"Total consecutive balance checks performed: {res['total_checks']}")
        print(f"Checks passed: {res['passed_checks']}")
        print(f"Pass rate: {res['pass_percentage']:.2f}%")
    else:
        print("Not enough data to perform running balance checks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate extracted bank statement CSV or JSON.")
    parser.add_argument("file_path", help="Path to the transactions CSV or JSON file")
    args = parser.parse_args()
    
    validate_statement(args.file_path)
