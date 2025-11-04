import pytest
import pandas as pd
import numpy as np
from src.modeling.strategy_signals import gap_trading_signal, breakout_signal, generate_signals

@pytest.fixture
def sample_ohlcv():
    dates = pd.date_range(start="2023-01-01", periods=30)
    data = {
        'Open': np.random.uniform(100, 110, 30),
        'High': np.random.uniform(110, 120, 30),
        'Low': np.random.uniform(90, 100, 30),
        'Close': np.linspace(100, 130, 30),
        'Volume': np.random.randint(1000, 2000, 30)
    }
    df = pd.DataFrame(data, index=dates)
    return df

def test_gap_trading_signal(sample_ohlcv):
    df = gap_trading_signal(sample_ohlcv.copy(), gap_threshold=0.02)
    assert 'gap_signal' in df.columns
    assert df['gap_signal'].isin([-1, 0, 1]).all()

def test_breakout_signal(sample_ohlcv):
    df = breakout_signal(sample_ohlcv.copy(), window=5)
    assert 'high_break' in df.columns
    assert 'low_break' in df.columns
    assert df['high_break'].isin([0, 1]).all()
    assert df['low_break'].isin([0, 1]).all()

def test_generate_signals(sample_ohlcv):
    df = generate_signals(sample_ohlcv.copy())
    assert 'gap_signal' in df.columns
    assert 'high_break' in df.columns
    assert 'low_break' in df.columns
