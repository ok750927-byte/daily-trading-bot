import pytest
import pandas as pd
import numpy as np
from src.modeling.feature_engineering import create_target, split_data

@pytest.fixture
def sample_data():
    """Fixture for creating a sample dataframe for testing."""
    dates = pd.to_datetime(pd.date_range(start="2023-01-01", periods=20))
    data = {
        'date': dates,
        'code': ['A'] * 10 + ['B'] * 10,
        'Close': list(range(100, 110)) + list(range(200, 210)),
        'ma5': np.random.rand(20),
        'volume_ma5': np.random.rand(20)
    }
    return pd.DataFrame(data)

def test_create_target(sample_data):
    """Test the create_target function."""
    df_with_target = create_target(sample_data, period=3)

    assert 'target' in df_with_target.columns
    assert 'future_return' in df_with_target.columns
    
    # Check if the last 'period' rows are dropped for each group
    assert len(df_with_target) == len(sample_data) - (2 * 3) # 2 groups * 3 days
    
    # Check target value logic
    # For stock A, price always increases, so target should be 1
    assert df_with_target[df_with_target['code'] == 'A']['target'].unique() == [1]

def test_split_data(sample_data):
    """Test the split_data function."""
    df_with_target = create_target(sample_data, period=3)
    
    features = ['ma5', 'volume_ma5']
    target = 'target'
    
    X_train, X_test, y_train, y_test, scaler = split_data(
        df_with_target, features, target, test_size=0.25, random_state=42
    )

    assert len(X_train) == 10
    assert len(X_test) == 4
    assert len(y_train) == 10
    assert len(y_test) == 4
    
    # Check if data is scaled (mean approx 0, std dev approx 1)
    # StandardScaler calculates population std dev (ddof=0)
    assert np.allclose(X_train.mean(axis=0), 0, atol=1e-8)
    assert np.allclose(X_train.std(axis=0, ddof=0), 1, atol=1e-8)
    assert scaler is not None
