import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hemmah_pro_ivs_2025 import HemmahDataEngine, HemmahMLEngine


def build_sample_df():
    return pd.DataFrame(
        {
            "price": [100000, 120000, 140000, 140000],
            "area": [100, 120, 140, 140],
            "district": ["A", "A", "B", "B"],
            "rooms": [3, 4, 5, None],
        }
    )


def test_clean_and_engineer_handles_duplicate_bins():
    engine = HemmahDataEngine()
    engine.raw_data = build_sample_df()

    engine.clean_and_engineer()

    assert engine.processed_data is not None
    assert "price_per_sqm" in engine.processed_data.columns
    assert "district_avg_price" in engine.processed_data.columns
    assert "district_tier" in engine.processed_data.columns


def test_get_modeling_data_drops_missing_values():
    engine = HemmahDataEngine()
    engine.raw_data = build_sample_df()
    engine.clean_and_engineer()

    model_df, features, target = engine.get_modeling_data()

    assert target == "price_per_sqm"
    assert model_df.isna().sum().sum() == 0
    assert "rooms" in features


def test_predict_and_sensitivity_analysis_are_stable():
    engine = HemmahDataEngine()
    engine.raw_data = build_sample_df()
    engine.clean_and_engineer()
    model_df, features, _ = engine.get_modeling_data()

    class DummyModel:
        def predict(self, x_data):
            return np.full(len(x_data), 500.0)

    ml = HemmahMLEngine()
    ml.best_model = DummyModel()
    ml.best_model_name = "Dummy"
    ml.metrics = {"test_r2": 0.9}

    sample = model_df[features].head(1)
    result = ml.predict(sample)

    assert result["predicted_price_per_sqm"] == 500.0
    assert result["confidence_interval"]["lower"] == 425.0
    assert result["confidence_interval"]["upper"] == 575.0

    sensitivity = ml.sensitivity_analysis(sample, features[0], variations=[-0.1, 0, 0.1])
    assert list(sensitivity["predicted_value"]) == [500.0, 500.0, 500.0]
