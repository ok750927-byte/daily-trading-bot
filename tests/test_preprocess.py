import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pandas as pd
from models import preprocess


def test_add_moving_average_and_rsi():
    df = pd.DataFrame({'Close': [10, 11, 12, 11, 13]})
    df = preprocess.add_moving_average(df, column='Close', window=3)
    df = preprocess.add_rsi(df, column='Close', window=3)
    assert 'MA_3' in df.columns
    assert 'RSI_3' in df.columns
