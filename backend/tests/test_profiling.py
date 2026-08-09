import pandas as pd

from agents.profiling_agent import build_dataset_profile, infer_column_type


def test_infers_column_types_correctly():
    df = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=10),
        "CustomerID": [f"C{i}" for i in range(10)],
        "Region": ["North", "South"] * 5,
        "Revenue": range(100, 110),
    })
    profile = build_dataset_profile(df, "sample.csv")
    types = {c.name: c.inferred_type for c in profile.columns}
    assert types["Date"] == "datetime"
    assert types["CustomerID"] == "id"
    assert types["Region"] == "categorical"
    assert types["Revenue"] == "numeric"


def test_quality_score_penalizes_missing_and_duplicates():
    df = pd.DataFrame({"A": [1, 2, None, 4, 5] * 4, "B": [1, 2, 3, 4, 5] * 4})
    df = pd.concat([df, df.iloc[:3]])  # add duplicates
    profile = build_dataset_profile(df, "dirty.csv")
    assert profile.quality.score < 100
    assert profile.quality.duplicate_rows >= 3


def test_clean_data_scores_high():
    df = pd.DataFrame({"A": range(100), "B": range(100, 200)})
    profile = build_dataset_profile(df, "clean.csv")
    assert profile.quality.score >= 95


def test_negative_values_flagged_for_revenue_like_column():
    df = pd.DataFrame({"Revenue": [100, 200, -50, 300, 400] * 10})
    profile = build_dataset_profile(df, "neg.csv")
    kinds = [i.kind for i in profile.quality.issues]
    assert "negative_values" in kinds
