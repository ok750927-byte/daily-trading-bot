import importlib
import sys
import os

# ensure repo root is on path
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root not in sys.path:
    sys.path.insert(0, root)

modules = [
    'src.trading.realtime_trader',
    'src.trading.risk_manager',
    'src.trading.broker_adapter',
]

for m in modules:
    try:
        importlib.import_module(m)
        print(f'OK: {m}')
    except Exception as e:
        print(f'ERR: {m} -> {e}')
        sys.exit(2)
print('ALL IMPORTS OK')
