import argparse
import json
import time
from pathlib import Path
import fitz  # pymupdf
import pandas as pd

# Import from app.py
from app import extract_text, process_statement, get_ocr_reader

def extract_text_eval(pdf_path, preset):
    """Extracts text depending on whether it's a clean text-based PDF or a noisy image-based PDF."""
    if preset == 'clean':
        with open(pdf_path, 'rb') as f:
            text = extract_text(f.read(), pdf_path.name)
            # If the PDF reader couldn't get text, it returns an error message starting with 'PDF appears'
            if "appears to be scanned" not in text:
                return text
    
    # Rasterize using pymupdf and use easyocr
    doc = fitz.open(pdf_path)
    reader = get_ocr_reader()
    full_text = ""
    for page in doc:
        # Render page at 150 DPI
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        result = reader.readtext(img_bytes, detail=0)
        full_text += "\n".join(result) + "\n"
    return full_text

def compare_transactions(pred_txs, true_txs):
    """Compares the extracted transactions against ground truth."""
    matched_dates = 0
    matched_amounts = 0
    matched_types = 0
    matched_balances = 0
    
    limit = min(len(pred_txs), len(true_txs))
    
    for i in range(limit):
        pred = pred_txs[i]
        true = true_txs[i]
        
        # Check Date
        if pred.date == true.get('date', ''):
            matched_dates += 1
            
        # Check Amount
        true_amt = true.get('credit') if true.get('credit') is not None else true.get('debit')
        if true_amt is None: true_amt = 0.0
        if abs(pred.amount - true_amt) < 0.01:
            matched_amounts += 1
            
        # Check Type (Credit/Debit)
        true_type = 'Credit' if true.get('credit') is not None else 'Debit'
        if pred.type.strip().lower() == true_type.lower():
            matched_types += 1
            
        # Check Balance
        true_bal = true.get('balance', 0.0)
        if abs(pred.balance - true_bal) < 0.01:
            matched_balances += 1
            
    return {
        "matched_dates": matched_dates,
        "matched_amounts": matched_amounts,
        "matched_types": matched_types,
        "matched_balances": matched_balances,
        "pred_len": len(pred_txs),
        "true_len": len(true_txs)
    }

def main():
    parser = argparse.ArgumentParser(description="Evaluate Bank Statement Parser against synthetic ground truth.")
    parser.add_argument("--data-dir", type=str, default="bank_statement_generator/output", help="Directory containing PDFs and JSON.")
    parser.add_argument("--preset", type=str, default="all", choices=["all", "clean", "light", "medium", "heavy"], help="Noise preset to evaluate.")
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    gt_file = data_dir / "all_statements.json"
    
    if not gt_file.exists():
        print(f"Ground truth file not found: {gt_file}")
        return
        
    with open(gt_file, 'r') as f:
        ground_truths = json.load(f)
        
    presets_to_eval = ["clean", "light", "medium", "heavy"] if args.preset == "all" else [args.preset]
    
    all_metrics = {}
    
    for preset in presets_to_eval:
        print(f"\\nEvaluating {len(ground_truths)} statements for preset: '{preset}'")
        
        total_dates = 0
        total_amts = 0
        total_types = 0
        total_bals = 0
        total_pred = 0
        total_true = 0
        success_count = 0
        
        for i, gt in enumerate(ground_truths):
            pdf_path = data_dir / f"stmt_{i+1:04d}_{preset}.pdf"
            if not pdf_path.exists():
                if args.preset != "all":
                    print(f"Skipping {pdf_path.name} (file not found)")
                continue
                
            print(f"-> Processing {pdf_path.name} ...")
            t0 = time.time()
            text = extract_text_eval(pdf_path, preset)
            
            try:
                parsed_result, _ = process_statement(text)
                metrics = compare_transactions(parsed_result.transactions, gt['transactions'])
                
                total_dates += metrics['matched_dates']
                total_amts += metrics['matched_amounts']
                total_types += metrics['matched_types']
                total_bals += metrics['matched_balances']
                total_pred += metrics['pred_len']
                total_true += metrics['true_len']
                success_count += 1
                
                print(f"   Extracted {metrics['pred_len']} / {metrics['true_len']} txs in {time.time()-t0:.1f}s")
                
            except Exception as e:
                print(f"   Failed to parse {pdf_path.name}: {e}")
                total_true += len(gt['transactions'])
            
            # Artificial pause to avoid hitting rate limits (e.g., ResourceExhausted)
            time.sleep(10)
                
        all_metrics[preset] = {
            "success": success_count,
            "total": len(ground_truths),
            "true_txs": total_true,
            "pred_txs": total_pred,
            "dates": total_dates,
            "amts": total_amts,
            "types": total_types,
            "bals": total_bals
        }

    print("\\n" + "="*50)
    print("FINAL EVALUATION METRICS")
    print("="*50)
    
    for preset, m in all_metrics.items():
        if m["total"] > 0 and (m["true_txs"] > 0 or m["pred_txs"] > 0):
            print(f"\\n--- PRESET: {preset.upper()} ---")
            print(f"Statements Parsed Successfully: {m['success']} / {m['total']}")
            print(f"Total True Transactions:        {m['true_txs']}")
            print(f"Total Extracted:                {m['pred_txs']}")
            
            if m["true_txs"] > 0:
                print(f"Transaction Extraction Rate:    {m['pred_txs']/m['true_txs']*100:.1f}%")
                
            if m["pred_txs"] > 0:
                print("Field Accuracy (percentage of extracted):")
                print(f"  Date Match:    {m['dates']/m['pred_txs']*100:.1f}%")
                print(f"  Amount Match:  {m['amts']/m['pred_txs']*100:.1f}%")
                print(f"  Type Match:    {m['types']/m['pred_txs']*100:.1f}%")
                print(f"  Balance Match: {m['bals']/m['pred_txs']*100:.1f}%")
        elif args.preset != "all":
            print(f"\\n--- PRESET: {preset.upper()} ---")
            print("No valid files found or processed for this preset.")

if __name__ == "__main__":
    main()
