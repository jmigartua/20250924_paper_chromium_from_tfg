import os
import pandas as pd
import importlib.util

# Resolve paths relative to repo root during tests
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
TEMPLATES = os.path.join(REPO_ROOT, "templates")

# Dynamically import schema_validator.py as a module
spec = importlib.util.spec_from_file_location("schema_validator", os.path.join(REPO_ROOT, "schema_validator.py"))
schema_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schema_validator)  # type: ignore[attr-defined]


def test_two_column_template():
    csv_path = os.path.join(TEMPLATES, "sample_two_column.csv")
    df = pd.read_csv(csv_path)
    sch = schema_validator.infer_schema(df, base_x_label="T (K)", selected_property="Normal Total Emittance")
    assert sch["mode"] == "two_col"
    assert sch["x_col"] is not None
    assert sch["y_cols"] and len(sch["y_cols"]) == 1


def test_grouped_long_template():
    csv_path = os.path.join(TEMPLATES, "sample_grouped_long.csv")
    df = pd.read_csv(csv_path)
    sch = schema_validator.infer_schema(df, base_x_label="λ (µm)", selected_property="Normal Spectral Reflectance")
    assert sch["mode"] == "grouped"
    assert sch["group_col"] is not None
    assert sch["x_col"] is not None
    assert sch["y_cols"] and len(sch["y_cols"]) == 1
    # Expect symmetric error column detected
    assert (sch["y_err"] is not None) or (sch["y_minus"] is not None and sch["y_plus"] is not None)


def test_wide_with_errors_template():
    csv_path = os.path.join(TEMPLATES, "sample_wide_with_errors.csv")
    df = pd.read_csv(csv_path)
    sch = schema_validator.infer_schema(df, base_x_label="λ (µm)", selected_property="Normal Spectral Reflectance")
    assert sch["mode"] == "wide"
    assert sch["x_col"] is not None
    assert sch["y_cols"] and len(sch["y_cols"]) >= 2  # R_s and R_p should be detected
