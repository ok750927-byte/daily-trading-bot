import multiprocessing as mp
import sys
import traceback
from typing import Any, Dict


def _worker(code: str, ctx: Dict, q: mp.Queue):
    # Restrict builtins
    safe_builtins = {
        'range': range,
        'len': len,
        'min': min,
        'max': max,
        'sum': sum,
        'abs': abs,
        'float': float,
        'int': int,
        'print': print,
        'sorted': sorted,
    }
    try:
        globs = {'__builtins__': safe_builtins}
        # provide a limited API object
        globs['ctx'] = ctx
        locs = {}
        # Execute the user code
        exec(code, globs, locs)
        # If code defines a 'run' callable, call it
        if 'run' in locs and callable(locs['run']):
            try:
                res = locs['run'](ctx)
            except Exception as e:
                q.put({'error': f'run() raised: {e}', 'trace': traceback.format_exc()})
                return
            q.put({'result': res})
            return
        # Otherwise, return locals snapshot (filtered)
        q.put({'result': {k: type(v).__name__ for k, v in locs.items()}})
    except Exception:
        q.put({'error': 'exception', 'trace': traceback.format_exc()})


def run_strategy(code: str, ctx: Dict = None, timeout: int = 5) -> Dict[str, Any]:
    """Run code string in a sandboxed process with a timeout. Returns a dict with 'result' or 'error'.
    The provided `ctx` is available as `ctx` inside the user code.
    """
    if ctx is None:
        ctx = {}
    q: mp.Queue = mp.Queue()
    p = mp.Process(target=_worker, args=(code, ctx, q), daemon=True)
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join(1)
        return {'error': 'timeout', 'trace': 'Execution exceeded timeout'}
    try:
        if not q.empty():
            return q.get_nowait()
        else:
            return {'result': None}
    except Exception as e:
        return {'error': str(e)}
