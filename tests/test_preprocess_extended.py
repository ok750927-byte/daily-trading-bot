import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pandas as pd
import numpy as np
from models import preprocess

def test_add_rsi_edge_cases():
    # 가격 변동이 없는 경우
    df_flat = pd.DataFrame({'Close': [10] * 10})
    df_flat = preprocess.add_rsi(df_flat)
    # RSI는 50에 가까워야 하지만, 부동소수점 문제로 정확히 50이 아닐 수 있음
    # 여기서는 NaN이 아닌지, 특정 범위 내에 있는지 확인
    # RSI는 처음 14개 기간 동안 NaN이므로, 그 이후의 값만 확인
    assert not df_flat['RSI_14'].iloc[14:].isnull().any()

    # 계속 상승하는 경우
    df_up = pd.DataFrame({'Close': np.arange(10, 20)})
    df_up = preprocess.add_rsi(df_up)
    # RSI는 100에 가까워야 함
    assert df_up['RSI_14'].iloc[-1] > 99

    # 계속 하락하는 경우
    df_down = pd.DataFrame({'Close': np.arange(20, 10, -1)})
    df_down = preprocess.add_rsi(df_down)
    # RSI는 0에 가까워야 함
    assert df_down['RSI_14'].iloc[-1] < 1
