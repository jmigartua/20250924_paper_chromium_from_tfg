# app_01_data_import.py
# ==============================================================================
# Comparative Material Properties Explorer (robust uploads with schema inference)
# - Base data: pickle-safe cache (plain dicts) + underscore-aware filename parsing
# - Uploads: robust structure detection (2-col / grouped-long / wide-multiY)
# - Uncertainties: symmetric and asymmetric error bars auto-detected
# ==============================================================================

from __future__ import annotations

import io
import os
import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ------------------------------------------------------------------------------
# Streamlit page config
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Comparative Data Explorer", layout="wide")

# If you previously cached a non-pickleable object, clear once then re-comment.
# st.cache_data.clear()


# ------------------------------------------------------------------------------
# Controlled vocabulary
# ------------------------------------------------------------------------------
KNOWN_MATERIALS = ["Chromium", "ChromiumOxides"]
KNOWN_PROPERTIES = [
    "Hemispherical Total Emittance",
    "Normal Total Emittance",
    "Normal Spectral Emittance",
    "Normal Spectral Reflectance",
    "Angular Spectral Reflectance",
    "Normal Spectral Absorptance",
    "Normal Solar Absorptance",
    "Normal Spectral Transmittance",
]


def _underscored(name: str) -> str:
    return name.replace(" ", "_")


def _clean(s: str) -> str:
    """Normalize col names for matching: lower, remove accents, strip units, collapse non-alnum."""
    if s is None:
        return ""
    x = s
    # remove content in parentheses (units)
    x = re.sub(r"\([^)]*\)", "", x)
    # normalize greek symbols to ascii tokens
    greek_map = {"ε": "epsilon", "λ": "lambda", "ρ": "rho", "α": "alpha", "τ": "tau"}
    for g, a in greek_map.items():
        x = x.replace(g, a)
    x = x.lower().strip()
    x = re.sub(r"[^a-z0-9]+", "_", x)
    return x.strip("_")


def _tokens(s: str) -> List[str]:
    return [t for t in _clean(s).split("_") if t]


def _similar(a: str, b: str) -> float:
    """Simple token-overlap similarity in [0,1]."""
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ------------------------------------------------------------------------------
# Base data loader (pickle-safe)
# ------------------------------------------------------------------------------
@st.cache_data
def load_base_data(data_dir: str = "data") -> Optional[Dict[str, Dict[str, Dict[str, pd.DataFrame]]]]:
    if not os.path.isdir(data_dir):
        return None
    db: Dict[str, Dict[str, Dict[str, pd.DataFrame]]] = {}
    for filename in sorted(os.listdir(data_dir)):
        if not filename.endswith(".csv"):
            continue
        base = filename[:-4]
        mat = next((m for m in KNOWN_MATERIALS if base.startswith(m + "_")), None)
        if mat is None:
            continue
        prop_part = base[len(mat) + 1 :]
        prop, subgroup = None, "default"
        for p in KNOWN_PROPERTIES:
            p_us = _underscored(p)
            if prop_part.startswith(p_us):
                prop = p
                tail = prop_part[len(p_us) :].lstrip("_")
                if tail:
                    subgroup = tail
                break
        if prop is None:
            st.warning(f"Unrecognized property in file '{filename}'. Skipped.")
            continue
        pth = os.path.join(data_dir, filename)
        try:
            df = pd.read_csv(pth)
        except Exception as e:
            st.error(f"Failed to load '{filename}': {e}")
            continue
        db.setdefault(mat, {}).setdefault(prop, {})[subgroup] = df
    return db


# ------------------------------------------------------------------------------
# Helpers: export & base X/Y choice
# ------------------------------------------------------------------------------
def prepare_csv_export(df: Optional[pd.DataFrame]) -> Optional[bytes]:
    if df is None or df.empty:
        return None
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")


def choose_xy_columns(df: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
    if df is None or df.empty:
        return None, None
    cols = list(df.columns)
    if len(cols) >= 3 and cols[0].lower().strip() == "curve":
        return cols[1], cols[2]
    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if len(numeric_cols) >= 2:
        return numeric_cols[0], numeric_cols[1]
    return None, None


# ------------------------------------------------------------------------------
# Upload parsing: infer schema (2-col / grouped-long / wide-multiY + errors)
# ------------------------------------------------------------------------------
def _y_synonyms_for_property(selected_property: str) -> List[str]:
    p = selected_property.lower()
    syn = []
    if "emiss" in p:  # emissivity/emittance
        syn += ["emissivity", "emittance", "epsilon", "eps"]
    if "reflect" in p:
        syn += ["reflectance", "rho", "r"]
    if "absorpt" in p:
        syn += ["absorptance", "alpha", "a"]
    if "transmit" in p:
        syn += ["transmittance", "tau", "t"]
    # Always allow generic y/intensity
    syn += ["y", "intensity", "signal", "value"]
    return syn


def _x_synonyms_for_base_x(base_x_label: str) -> List[str]:
    bx = base_x_label.lower() if base_x_label else ""
    syn = ["x"]
    if "temp" in bx or "(k)" in bx or bx.strip() in {"t", "t k"}:
        syn += ["t", "temperature", "temp", "t_k", "k"]
    if "wave" in bx or "lambda" in bx or "lam" in bx or "µm" in bx or "um" in bx:
        syn += ["wavelength", "lambda", "lam", "wl", "micron", "um", "µm"]
    if "wavenumber" in bx or "cm" in bx:
        syn += ["wavenumber", "1_cm", "cm_1", "k", "nu"]
    return syn


def _find_column_by_synonyms(df: pd.DataFrame, synonyms: List[str]) -> Optional[str]:
    scores = []
    for c in df.columns:
        cs = _clean(c)
        score = 0.0
        for syn in synonyms:
            score = max(score, _similar(cs, syn))
        scores.append((score, c))
    scores.sort(reverse=True, key=lambda t: t[0])
    if scores and scores[0][0] >= 0.34:  # modest threshold
        return scores[0][1]
    return None


def _first_two_numeric(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(num) >= 2:
        return num[0], num[1]
    return None, None


def _detect_error_columns(df: pd.DataFrame, y_col: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Try to detect symmetric (y_err) or asymmetric (y_minus, y_plus) error columns.
    Priority:
      1) asymmetric: y_lower/y_upper or y_minus/y_plus
      2) symmetric: y_err / err / std / sigma / uncertainty
      3) generic 'err' column if unique
    """
    cols = list(df.columns)
    y_clean = _clean(y_col)

    # Candidates by pattern next to y stem
    minus_candidates = [c for c in cols if re.search(r"(minus|lower|lo|min)$", _clean(c))]
    plus_candidates = [c for c in cols if re.search(r"(plus|upper|hi|max)$", _clean(c))]

    # Try to bind asymmetric to y stem
    y_minus = next((c for c in minus_candidates if _similar(_clean(c), y_clean) >= 0.34), None)
    y_plus = next((c for c in plus_candidates if _similar(_clean(c), y_clean) >= 0.34), None)
    if y_minus and y_plus:
        return None, y_minus, y_plus

    # Symmetric errors tied to y
    err_names = ["err", "error", "sigma", "std", "stderr", "uncert", "uncertainty"]
    y_err = None
    candidates = []
    for c in cols:
        cc = _clean(c)
        if any(name in cc for name in err_names):
            candidates.append(c)
    # Prefer one whose tokens overlap with y
    candidates.sort(key=lambda c: _similar(_clean(c), y_clean), reverse=True)
    if candidates:
        y_err = candidates[0]
        return y_err, None, None

    # Fallback: a single column literally named 'err' (rare)
    if "err" in [c.lower() for c in cols]:
        return "err", None, None

    return None, None, None


def detect_uploaded_structure(
    df: pd.DataFrame,
    base_x_label: str,
    selected_property: str,
) -> dict:
    """
    Infer schema:
      - mode: 'two_col' | 'grouped' | 'wide'
      - x_col, y_cols (list), group_col (optional)
      - y_err (optional), y_minus (optional), y_plus (optional)
    """
    result = {
        "mode": None,
        "x_col": None,
        "y_cols": [],
        "group_col": None,
        "y_err": None,
        "y_minus": None,
        "y_plus": None,
        "notes": [],
    }

    cols = list(df.columns)

    # 0) If a grouping column exists, prefer it
    group_candidates = ["curve", "series", "label", "group", "dataset", "name"]
    group_col = _find_column_by_synonyms(df, group_candidates)
    if group_col:
        result["group_col"] = group_col

    # 1) Try to align with base axes
    x_syn = _x_synonyms_for_base_x(base_x_label)
    y_syn = _y_synonyms_for_property(selected_property)

    x_col = _find_column_by_synonyms(df, x_syn)
    y_col = _find_column_by_synonyms(df, y_syn)

    # 2) If not found, heuristics
    if x_col is None:
        x_col, _ = _first_two_numeric(df)
    if y_col is None:
        # pick the first numeric column ≠ x
        num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and c != x_col]
        if num:
            y_col = num[0]

    # 3) If still not found, fallback to raw first two columns
    if x_col is None or y_col is None:
        if df.shape[1] >= 2:
            x_col = x_col or cols[0]
            y_col = y_col or cols[1]
            result["notes"].append("Fallback to first two columns.")
        else:
            result["notes"].append("Insufficient columns.")
            result["mode"] = "invalid"
            return result

    # 4) Detect whether wide (single X + multiple Y numeric columns)
    #    Wide if there are ≥2 numeric columns besides X and no group col.
    other_numeric = [c for c in cols if c != x_col and pd.api.types.is_numeric_dtype(df[c])]
    if not group_col and len(other_numeric) >= 2:
        result["mode"] = "wide"
        result["x_col"] = x_col
        # Choose Y columns that are not obvious error columns
        err_kw = ("err", "error", "sigma", "std", "uncert")
        y_cols = [c for c in other_numeric if not any(k in _clean(c) for k in err_kw)]
        if not y_cols:
            y_cols = other_numeric[:1]  # at least one
        result["y_cols"] = y_cols
        result["notes"].append(f"Wide format detected with {len(y_cols)} Y series.")
        return result

    # 5) Grouped-long if group column exists and (X,Y) are found
    if group_col:
        result["mode"] = "grouped"
        result["x_col"] = x_col
        result["y_cols"] = [y_col]
        y_err, y_minus, y_plus = _detect_error_columns(df, y_col)
        result["y_err"], result["y_minus"], result["y_plus"] = y_err, y_minus, y_plus
        return result

    # 6) Otherwise treat as two_col (or single Y series)
    result["mode"] = "two_col"
    result["x_col"] = x_col
    result["y_cols"] = [y_col]
    y_err, y_minus, y_plus = _detect_error_columns(df, y_col)
    result["y_err"], result["y_minus"], result["y_plus"] = y_err, y_minus, y_plus
    return result


# ------------------------------------------------------------------------------
# Session state for uploaded data (store df + parsed schema)
# ------------------------------------------------------------------------------
if "uploaded_parsed" not in st.session_state:
    # filename -> {"df": DataFrame, "schema": dict}
    st.session_state.uploaded_parsed = {}


# ------------------------------------------------------------------------------
# Load base data
# ------------------------------------------------------------------------------
db = load_base_data(data_dir="data")
if not db:
    st.error(
        "Fatal Error: `data/` directory not found or contains no recognizable CSVs.\n"
        "Add files like:\n  Chromium_Hemispherical_Total_Emittance.csv\n  Chromium_Normal_Total_Emittance_Annealed.csv"
    )
    st.stop()


# ------------------------------------------------------------------------------
# App title & description
# ------------------------------------------------------------------------------
st.title("Comparative Material Properties Explorer")
st.markdown(
    "Visualize **reference data** and compare with your **experimental results**. "
    "The uploader accepts: (i) plain 2-column CSVs, (ii) grouped/long tables with a series label, and "
    "(iii) wide tables with one X column and multiple Y series; uncertainties are detected when present."
)

# ------------------------------------------------------------------------------
# Sidebar — selection + uploads
# ------------------------------------------------------------------------------
st.sidebar.header("Data Selection")

materials = sorted(db.keys())
selected_material = st.sidebar.selectbox("Select Material", materials, index=0)

properties = sorted(db[selected_material].keys())
selected_property = st.sidebar.selectbox("Select Property", properties, index=0)

subgroups = sorted(db[selected_material][selected_property].keys())
selected_subgroup = (
    st.sidebar.selectbox("Select Condition/Subgroup", subgroups, index=0)
    if len(subgroups) > 1
    else subgroups[0]
)

st.sidebar.header("Compare with Your Data")
uploaded_files = st.sidebar.file_uploader(
    "Upload CSV file(s)",
    type="csv",
    accept_multiple_files=True,
    key="file_uploader",
)

with st.sidebar.expander("Accepted CSV shapes"):
    st.info(
        "- **2 columns:** X, Y (headers optional).  \n"
        "- **Grouped/long:** e.g., `Curve/Series`, `X`, `Y`, optional `Yerr` or `Yminus/Yplus`.  \n"
        "- **Wide:** one X column + multiple Y columns (optional per-series errors).  \n"
        "Common names recognized for uncertainties: `err`, `error`, `sigma`, `std`, `uncertainty`, as well as `lower/upper`, `minus/plus`."
    )

# Parse uploads
if uploaded_files:
    st.session_state.uploaded_parsed = {}
    # Base axis labels (to bias inference)
    base_df = db[selected_material][selected_property][selected_subgroup]
    bx, by = choose_xy_columns(base_df)
    base_x_label = bx or (base_df.columns[1] if base_df.shape[1] >= 2 else "X")
    for f in uploaded_files:
        try:
            udf = pd.read_csv(f)
        except Exception as e:
            st.sidebar.error(f"Error reading '{f.name}': {e}")
            continue
        schema = detect_uploaded_structure(udf, base_x_label, selected_property)
        if schema["mode"] == "invalid":
            st.sidebar.warning(f"'{f.name}' could not be interpreted (insufficient columns).")
            continue
        st.session_state.uploaded_parsed[f.name] = {"df": udf, "schema": schema}

# ------------------------------------------------------------------------------
# Header & base dataframe
# ------------------------------------------------------------------------------
header = f"{selected_property} of {selected_material}"
if selected_subgroup != "default":
    header += f" — Condition: {selected_subgroup}"
st.header(header)

base_df = db[selected_material][selected_property][selected_subgroup]
if base_df is None or base_df.empty:
    st.warning("Selected reference dataset is empty.")
    st.stop()

x_col_ref, y_col_ref = choose_xy_columns(base_df)
if x_col_ref is None or y_col_ref is None:
    st.error("Could not infer X/Y columns from the reference dataset.")
    st.stop()

# Reference curve selection
st.subheader("Reference Data Controls")
if "Curve" in base_df.columns:
    all_curves = list(base_df["Curve"].unique())
    selected_curves = st.multiselect(
        "Select reference curves to plot",
        options=all_curves,
        default=all_curves,
    )
    ref_df = base_df[base_df["Curve"].isin(selected_curves)] if selected_curves else base_df.iloc[0:0]
else:
    st.info("No 'Curve' column found; plotting the entire reference dataset.")
    ref_df = base_df.copy()

with st.expander("Preview reference data"):
    st.dataframe(base_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# Plot
# ------------------------------------------------------------------------------
st.subheader("Interactive Comparison Plot")
fig = go.Figure()
any_plotted = False

# (1) Reference data
if not ref_df.empty:
    if "Curve" in ref_df.columns:
        for cname, cdf in ref_df.groupby("Curve"):
            fig.add_trace(
                go.Scatter(
                    x=cdf[x_col_ref],
                    y=cdf[y_col_ref],
                    mode="lines+markers",
                    name=f"{cname} (Ref)",
                )
            )
    else:
        fig.add_trace(
            go.Scatter(
                x=ref_df[x_col_ref],
                y=ref_df[y_col_ref],
                mode="lines+markers",
                name="Reference",
            )
        )
    any_plotted = True

# (2) Uploaded user data (robust handling)
if st.session_state.uploaded_parsed:
    for fname, bundle in st.session_state.uploaded_parsed.items():
        udf, sch = bundle["df"], bundle["schema"]
        mode = sch["mode"]
        x = sch["x_col"]
        y_cols = sch["y_cols"]
        group_col = sch["group_col"]
        y_err, y_minus, y_plus = sch["y_err"], sch["y_minus"], sch["y_plus"]

        if mode == "two_col":
            y = y_cols[0]
            err_kwargs = {}
            if y_minus and y_plus and pd.api.types.is_numeric_dtype(udf[y_minus]) and pd.api.types.is_numeric_dtype(udf[y_plus]):
                err_kwargs["error_y"] = dict(
                    type="data",
                    array=(udf[y_plus] - udf[y]).abs(),
                    arrayminus=(udf[y] - udf[y_minus]).abs(),
                    visible=True,
                )
            elif y_err and pd.api.types.is_numeric_dtype(udf[y_err]):
                err_kwargs["error_y"] = dict(type="data", array=udf[y_err].abs(), visible=True)

            fig.add_trace(
                go.Scatter(
                    x=udf[x],
                    y=udf[y],
                    mode="markers",
                    name=os.path.splitext(fname)[0],
                    **err_kwargs,
                )
            )
            any_plotted = True

        elif mode == "grouped":
            y = y_cols[0]
            for g, gdf in udf.groupby(group_col):
                err_kwargs = {}
                if y_minus and y_plus and pd.api.types.is_numeric_dtype(gdf[y_minus]) and pd.api.types.is_numeric_dtype(gdf[y_plus]):
                    err_kwargs["error_y"] = dict(
                        type="data",
                        array=(gdf[y_plus] - gdf[y]).abs(),
                        arrayminus=(gdf[y] - gdf[y_minus]).abs(),
                        visible=True,
                    )
                elif y_err and pd.api.types.is_numeric_dtype(gdf[y_err]):
                    err_kwargs["error_y"] = dict(type="data", array=gdf[y_err].abs(), visible=True)

                fig.add_trace(
                    go.Scatter(
                        x=gdf[x],
                        y=gdf[y],
                        mode="markers",
                        name=f"{os.path.splitext(fname)[0]} — {g}",
                        **err_kwargs,
                    )
                )
            any_plotted = True

        elif mode == "wide":
            # One X + multiple Y series; look for per-series error companions
            for y in y_cols:
                err_kwargs = {}
                # Seek y-specific error columns like y_err / y_minus / y_plus
                # by matching stems in cleaned names
                ystem = _clean(y)
                colmap = {c: _clean(c) for c in udf.columns}

                # asymmetric
                y_minus_cand = next((c for c, cc in colmap.items() if ystem in cc and re.search(r"(minus|lower|lo|min)$", cc)), None)
                y_plus_cand = next((c for c, cc in colmap.items() if ystem in cc and re.search(r"(plus|upper|hi|max)$", cc)), None)
                if y_minus_cand and y_plus_cand:
                    if pd.api.types.is_numeric_dtype(udf[y_minus_cand]) and pd.api.types.is_numeric_dtype(udf[y_plus_cand]):
                        err_kwargs["error_y"] = dict(
                            type="data",
                            array=(udf[y_plus_cand] - udf[y]).abs(),
                            arrayminus=(udf[y] - udf[y_minus_cand]).abs(),
                            visible=True,
                        )
                else:
                    # symmetric
                    cand = next(
                        (
                            c
                            for c, cc in colmap.items()
                            if ystem in cc and any(k in cc for k in ["err", "error", "sigma", "std", "uncert"])
                        ),
                        None,
                    )
                    if cand and pd.api.types.is_numeric_dtype(udf[cand]):
                        err_kwargs["error_y"] = dict(type="data", array=udf[cand].abs(), visible=True)

                fig.add_trace(
                    go.Scatter(
                        x=udf[x],
                        y=udf[y],
                        mode="markers",
                        name=f"{os.path.splitext(fname)[0]} — {y}",
                        **err_kwargs,
                    )
                )
            any_plotted = True

# Show plot
if any_plotted:
    fig.update_layout(
        title="Comparison Plot",
        xaxis_title=str(x_col_ref),
        yaxis_title=str(y_col_ref),
        legend_title="Datasets",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select reference curves or upload data to generate a plot.")

# ------------------------------------------------------------------------------
# Upload parsing summary (for transparency/debugging)
# ------------------------------------------------------------------------------
if st.session_state.uploaded_parsed:
    st.subheader("Upload Parsing Summary")
    rows = []
    for fname, bundle in st.session_state.uploaded_parsed.items():
        sch = bundle["schema"]
        rows.append(
            {
                "file": fname,
                "mode": sch["mode"],
                "x_col": sch["x_col"],
                "y_cols": ", ".join(sch["y_cols"]),
                "group_col": sch["group_col"] or "",
                "y_err": sch["y_err"] or "",
                "y_minus": sch["y_minus"] or "",
                "y_plus": sch["y_plus"] or "",
                "notes": "; ".join(sch["notes"]) if sch["notes"] else "",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# Export (reference selection)
# ------------------------------------------------------------------------------
st.subheader("Data Export")
export_source = ref_df if not ref_df.empty else None
csv_bytes = prepare_csv_export(export_source)
parts = [selected_material, selected_property]
if selected_subgroup != "default":
    parts.append(selected_subgroup)
safe_filename = "Reference_" + "_".join(p.replace(" ", "_") for p in parts) + ".csv"

if csv_bytes:
    st.download_button(
        label="📥 Download Selected Reference Data",
        data=csv_bytes,
        file_name=safe_filename,
        mime="text/csv",
    )
else:
    st.markdown("_Select at least one reference curve (or ensure the dataset is not empty) to enable downloading._")
