"""
Bank Statement Generator + PDF Renderer + OCR Noise Pipeline
=============================================================
Generates synthetic Indian bank statements as realistic PDFs,
then applies configurable noise/degradation for OCR testing.

Usage:
    python generator.py [options]

Options:
    --count N          Number of statements to generate (default: 5)
    --preset PRESET    Noise preset: clean | light | heavy
    --all-presets      Generate one copy per preset
    --month YYYY-MM    Statement month (default: 2024-03)
    --bank NAME        Bank name (default: random)
    --persona TYPE     salaried | freelance | highspend | lowspend (default: salaried)
    --out-dir DIR      Output directory (default: ./output)
    --seed N           Random seed for reproducibility
    --json-only        Only output JSON, skip PDF rendering
"""

import argparse
import json
import random
from pathlib import Path

from data_gen import BANK_NAMES, generate_statement
from pdf_render import render_pdf
from noise_fx import PRESETS, apply_noise

def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--count",       type=int,   default=5,         help="Number of statements")
    p.add_argument("--preset",      type=str,   default="heavy",  help="Noise preset")
    p.add_argument("--all-presets", action="store_true",           help="Generate all 4 presets")
    p.add_argument("--month",       type=str,   default="2024-03", help="YYYY-MM")
    p.add_argument("--bank",        type=str,   default=None,      help="Bank name")
    p.add_argument("--persona",     type=str,   default="salaried",help="Persona type")
    p.add_argument("--init-balance",type=float, default=45000,     help="Initial balance")
    p.add_argument("--tx-count",    type=int,   default=40,        help="Target transactions")
    p.add_argument("--debit-ratio", type=float, default=0.75,      help="Debit ratio 0-1")
    p.add_argument("--edge-density",type=float, default=0.05,      help="Edge case density 0-1")
    p.add_argument("--overdraft",   action="store_true",           help="Allow overdraft")
    p.add_argument("--out-dir",     type=str,   default="./output",help="Output directory")
    p.add_argument("--seed",        type=int,   default=None,      help="Base random seed")
    p.add_argument("--json-only",   action="store_true",           help="Skip PDF rendering")
    return p.parse_args()

def main():
    args     = parse_args()
    out_dir  = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_seed  = args.seed if args.seed is not None else random.randint(0, 2**31)
    bank_names = [args.bank] * args.count if args.bank else \
                 [BANK_NAMES[i % len(BANK_NAMES)] for i in range(args.count)]

    presets_to_use = list(PRESETS.values()) if args.all_presets else [PRESETS[args.preset]]

    all_stmts = []
    print(f"Generating {args.count} statement(s)...")

    for i in range(args.count):
        seed  = base_seed + i * 7919
        stmt  = generate_statement(
            bank_name     = bank_names[i],
            month_str     = args.month,
            init_balance  = args.init_balance,
            tx_count      = args.tx_count,
            debit_ratio   = args.debit_ratio,
            edge_density  = args.edge_density,
            persona       = args.persona,
            allow_overdraft = args.overdraft,
            seed          = seed,
        )
        all_stmts.append(stmt)

        json_path = out_dir / f"stmt_{i+1:04d}.json"
        json_path.write_text(json.dumps(stmt, indent=2))

        if args.json_only:
            print(f"  [{i+1}/{args.count}] {stmt['account_holder']} -> {json_path.name}")
            continue

        print(f"  [{i+1}/{args.count}] {stmt['account_holder']} - rendering PDF...")
        clean_pdf = render_pdf(stmt)

        for preset in presets_to_use:
            if preset.name == "clean" or args.all_presets:
                if preset.name == "clean":
                    pdf_bytes = clean_pdf
                else:
                    print(f"             applying [{preset.name}] noise...")
                    pdf_bytes = apply_noise(clean_pdf, preset, seed=seed)
            else:
                print(f"             applying [{preset.name}] noise...")
                pdf_bytes = apply_noise(clean_pdf, preset, seed=seed)

            suffix   = f"_{preset.name}" if args.all_presets else f"_{preset.name}"
            pdf_path = out_dir / f"stmt_{i+1:04d}{suffix}.pdf"
            pdf_path.write_bytes(pdf_bytes)
            print(f"             -> {pdf_path.name} ({len(pdf_bytes)//1024} KB)")

    combined_path = out_dir / "all_statements.json"
    combined_path.write_text(json.dumps(all_stmts, indent=2))
    print(f"\\nDone. {args.count} statement(s) saved to {out_dir}/")
    print(f"Combined JSON -> {combined_path}")

if __name__ == "__main__":
    main()
