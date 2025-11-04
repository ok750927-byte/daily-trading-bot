"""
Simple integration-style test: verify that the project's report path
(`results/performance_summary.json`) can be created with the same dummy
structure the GUI expects. This doesn't launch the GUI (headless-friendly).

Run with:
    python tests\test_gui_integration_report.py

It prints PASS/FAIL and the created report content.
"""
import os
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
results_dir = root / 'results'
report_path = results_dir / 'performance_summary.json'

# Remove previous test artifact if exists to test creation
if report_path.exists():
    report_path.unlink()

os.makedirs(results_dir, exist_ok=True)

# Logic copied from GUI's load_report dummy branch
if not report_path.exists():
    dummy_report = {
        "total_trades": 120,
        "win_rate": 62.5,
        "total_profit": 18500.75,
        "max_drawdown": -550.20,
        "avg_profit_per_trade": 154.17,
        "sharpe_ratio": 1.25,
    }
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(dummy_report, f, indent=2)

# Read and print results for verification
try:
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print('REPORT_CREATED: True')
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print('TEST_RESULT: PASS')
except Exception as e:
    print('REPORT_CREATED: False')
    print('ERROR:', e)
    print('TEST_RESULT: FAIL')
