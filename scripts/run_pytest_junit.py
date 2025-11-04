"""Run pytest programmatically and write junit xml results to a file.

This avoids shell redirection issues in some environments by using pytest's
built-in emitter to write an XML result file that can be parsed reliably.
"""
import sys
import os
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'pytest_junit_results.xml'

print('Running pytest and writing junit xml to:', OUTPUT)
args = ['tests', '-vv', '-rA', f'--junitxml={str(OUTPUT)}']
ret = pytest.main(args)
print('pytest exit code:', ret)
if OUTPUT.exists():
    print('Result file size:', OUTPUT.stat().st_size)
else:
    print('Result file not created')
sys.exit(ret)
