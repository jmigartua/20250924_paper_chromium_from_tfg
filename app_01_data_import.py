# app_01_data_import.py
# ==============================================================================
# Comparative Material Properties Explorer — Enhanced
# - Robust upload parsing (2-col / grouped-long / wide) + uncertainties
# - Units normalization (°C→K, nm→µm, cm⁻¹→µm) and percent→fraction for Y
# - Provenance & version export (JSON)
# - Documentation tabs rendering docs/*.md
# ==============================================================================

from __future__ import annotations

import io, os, re, json, platform, subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------------
st.set_page_config(page_title="Comparative Data Explorer", layout="wide")
# st.cache_data.clear()  # uncomment once if you need to invalidate stale cache

# ----------------------------------------------------------------------------
# Controlled vocabulary
# ----------------------------------------------------------------------------
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
    if s is None:
        return ""
    x = re.sub(r"\([^)]*\)", "", s)  # strip (...) units
    greek = {"ε": "epsilon", "λ": "lambda", "ρ": "rho", "α": "alpha", "τ": "tau"}
    for g,a in greek.items():
        x = x.replace(g, a)
    x = re.sub(r"[^a-zA-Z0-9]+", "_", x.lower()).strip("_")
    return x

def _tokens(s: str) -> List[str]:
    return [t for t in _clean(s).split("_") if t]

def _similar(a: str, b: str) -> float:
    ta, tb = set(_tokens(a)), set(_tokens(b))
    return 0.0 if not ta or not tb else len(ta & tb) / len(ta | tb)

# ----------------------------------------------------------------------------
# Cacheable base data loader (pickle-safe)
# ----------------------------------------------------------------------------
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

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
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

def _y_synonyms_for_property(selected_property: str) -> List[str]:
    p = selected_property.lower()
    syn = []
    if "emiss" in p: syn += ["emissivity","emittance","epsilon","eps"]
    if "reflect" in p: syn += ["reflectance","rho","r"]
    if "absorpt" in p: syn += ["absorptance","alpha","a"]
    if "transmit" in p: syn += ["transmittance","tau","t"]
    syn += ["y","intensity","signal","value"]
    return syn

def _x_synonyms_for_base_x(base_x_label: str) -> List[str]:
    bx = base_x_label.lower() if base_x_label else ""
    syn = ["x"]
    if "temp" in bx or "(k)" in bx or bx.strip() in {"t","t k"}: syn += ["t","temperature","temp","t_k","k"]
    if "wave" in bx or "lambda" in bx or "lam" in bx or "µm" in bx or "um" in bx:
        syn += ["wavelength","lambda","lam","wl","micron","um","µm"]
    if "wavenumber" in bx or "cm" in bx: syn += ["wavenumber","1_cm","cm_1","k","nu"]
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
    if scores and scores[0][0] >= 0.34:
        return scores[0][1]
    return None

def _first_two_numeric(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return (num[0], num[1]) if len(num) >= 2 else (None, None)

def _detect_error_columns(df: pd.DataFrame, y_col: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    cols = list(df.columns)
    y_clean = _clean(y_col)
    minus_candidates = [c for c in cols if re.search(r"(minus|lower|lo|min)$", _clean(c))]
    plus_candidates  = [c for c in cols if re.search(r"(plus|upper|hi|max)$", _clean(c))]
    y_minus = next((c for c in minus_candidates if _similar(_clean(c), y_clean) >= 0.34), None)
    y_plus  = next((c for c in plus_candidates  if _similar(_clean(c), y_clean) >= 0.34), None)
    if y_minus and y_plus:
        return None, y_minus, y_plus
    err_names = ["err","error","sigma","std","stderr","uncert","uncertainty"]
    candidates = [c for c in cols if any(name in _clean(c) for name in err_names)]
    candidates.sort(key=lambda c: _similar(_clean(c), y_clean), reverse=True)
    if candidates:
        return candidates[0], None, None
    if "err" in [c.lower() for c in cols]:
        return "err", None, None
    return None, None, None

def detect_uploaded_structure(df: pd.DataFrame, base_x_label: str, selected_property: str) -> dict:
    result = {"mode": None, "x_col": None, "y_cols": [], "group_col": None,
              "y_err": None, "y_minus": None, "y_plus": None, "notes": []}
    cols = list(df.columns)
    group_candidates = ["curve","series","label","group","dataset","name"]
    group_col = _find_column_by_synonyms(df, group_candidates)
    if group_col: result["group_col"] = group_col

    x_syn = _x_synonyms_for_base_x(base_x_label)
    y_syn = _y_synonyms_for_property(selected_property)
    x_col = _find_column_by_synonyms(df, x_syn)
    y_col = _find_column_by_synonyms(df, y_syn)

    if x_col is None: x_col, _ = _first_two_numeric(df)
    if y_col is None:
        num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and c != x_col]
        if num: y_col = num[0]

    if x_col is None or y_col is None:
        if df.shape[1] >= 2:
            x_col = x_col or cols[0]
            y_col = y_col or cols[1]
            result["notes"].append("Fallback to first two columns.")
        else:
            result["notes"].append("Insufficient columns.")
            result["mode"] = "invalid"
            return result

    other_numeric = [c for c in cols if c != x_col and pd.api.types.is_numeric_dtype(df[c])]
    if not group_col and len(other_numeric) >= 2:
        err_kw = ("err","error","sigma","std","uncert")
        y_cols = [c for c in other_numeric if not any(k in _clean(c) for k in err_kw)] or other_numeric[:1]
        result.update({"mode":"wide","x_col":x_col,"y_cols":y_cols})
        result["notes"].append(f"Wide format detected with {len(y_cols)} Y series.")
        return result

    if group_col:
        y_err,y_minus,y_plus = _detect_error_columns(df, y_col)
        result.update({"mode":"grouped","x_col":x_col,"y_cols":[y_col],
                       "y_err":y_err,"y_minus":y_minus,"y_plus":y_plus})
        return result

    y_err,y_minus,y_plus = _detect_error_columns(df, y_col)
    result.update({"mode":"two_col","x_col":x_col,"y_cols":[y_col],
                   "y_err":y_err,"y_minus":y_minus,"y_plus":y_plus})
    return result

# ----------------------------------------------------------------------------
# Units normalization helpers
# ----------------------------------------------------------------------------
def infer_base_x_semantics(x_label: str) -> tuple[str, str]:
    """Return (axis_type, base_units) where axis_type in {'temperature','wavelength','wavenumber','unknown'}."""
    lab = x_label or ""
    l = lab.lower()
    if "k)" in l or " t " in f" {l} " or "temp" in l:
        return "temperature", "K"
    if "cm" in l and "-1" in l:
        return "wavenumber", "cm^-1"
    if "µm" in l or "um" in l or "lambda" in l or "wavelength" in l:
        return "wavelength", "um"
    return "unknown", ""

def detect_input_units_from_header(col_name: str) -> Optional[str]:
    c = col_name.lower()
    if "°c" in c or "celsius" in c or "(c)" in c: return "C"
    if "(k)" in c: return "K"
    if "nm" in c or "(nm)" in c: return "nm"
    if "µm" in c or "um" in c: return "um"
    if "cm-1" in c or "cm⁻1" in c or "cm^-1" in c: return "cm^-1"
    return None

def convert_x_series(x: pd.Series, input_units: str, base_axis: str) -> pd.Series:
    """Convert X series to base axis units (if compatible)."""
    if base_axis == "temperature":
        if input_units == "C":
            return x + 273.15
        # K -> K or unknown/um/nm -> unchanged
        return x
    if base_axis == "wavelength":
        if input_units == "nm":
            return x / 1000.0
        if input_units == "cm^-1":
            # λ(µm) = 10^4 / ν(cm^-1)
            return 1.0e4 / x.replace(0, np.nan)
        return x
    if base_axis == "wavenumber":
        # For completeness, if base axis were wavenumber (rare), handle µm->cm^-1
        if input_units == "um":
            return 1.0e4 / x.replace(0, np.nan)
        if input_units == "nm":
            return 1.0e4 / (x/1000.0).replace(0, np.nan)
        return x
    return x

def normalize_y_and_errors(y: pd.Series, y_err: Optional[pd.Series], y_minus: Optional[pd.Series], y_plus: Optional[pd.Series], mode: str) -> tuple[pd.Series, Optional[pd.Series], Optional[pd.Series], Optional[pd.Series]]:
    """Percent → fraction normalization for y and its errors according to mode: 'off'|'auto'|'force'."""
    if mode == "off":
        return y, y_err, y_minus, y_plus
    must_scale = False
    if mode == "force":
        must_scale = True
    elif mode == "auto":
        # Heuristic: values in [1.5, 100] suggest percent; also headers may include '%'
        # Header-based detection is handled upstream; here do value-based.
        maxv = pd.to_numeric(y, errors="coerce").max()
        must_scale = (maxv is not None) and (maxv > 1.5) and (maxv <= 150.0)
    if must_scale:
        y = y / 100.0
        if y_err is not None:
            y_err = y_err / 100.0
        if y_minus is not None:
            y_minus = y_minus / 100.0
        if y_plus is not None:
            y_plus = y_plus / 100.0
    return y, y_err, y_minus, y_plus

# ----------------------------------------------------------------------------
# Session state for uploads
# ----------------------------------------------------------------------------
if "uploaded_parsed" not in st.session_state:
    st.session_state.uploaded_parsed = {}

# ----------------------------------------------------------------------------
# Load base data
# ----------------------------------------------------------------------------
db = load_base_data(data_dir="data")
if not db:
    st.error("`data/` not found or contains no recognizable CSVs. Add files like `Chromium_Normal_Total_Emittance.csv`.")
    st.stop()

# ----------------------------------------------------------------------------
# Sidebar: Help
# ----------------------------------------------------------------------------
st.sidebar.header("Help & Documentation")
with st.sidebar.expander("ℹ️ App overview & tips", expanded=False):
    st.markdown("""
- **Uploads accepted**: 2-col (X,Y); grouped/long (Curve, X, Y, [errors]); wide (one X, multiple Y* with per-series errors).
- **Uncertainties**: symmetric (`err/sigma/std/uncertainty`) and asymmetric (`minus/lower` & `plus/upper`).
- **Units normalization**: °C→K, nm→µm, cm⁻¹→µm, percent→fraction.
- See also the **Documentation** tabs at the bottom of the page.
""")

# ----------------------------------------------------------------------------
# Title & description
# ----------------------------------------------------------------------------
st.title("Comparative Material Properties Explorer — Enhanced")
st.markdown("Overlay curated **reference data** with your **experimental** CSVs. Supports uncertainties and optional units normalization.")

# ----------------------------------------------------------------------------
# Sidebar: Selection
# ----------------------------------------------------------------------------
st.sidebar.header("Data Selection")
materials = sorted(db.keys())
selected_material = st.sidebar.selectbox("Material", materials, index=0, help="Reference material class.")
properties = sorted(db[selected_material].keys())
selected_property = st.sidebar.selectbox("Property", properties, index=0, help="Thermo-optical property to inspect.")
subgroups = sorted(db[selected_material][selected_property].keys())
selected_subgroup = st.sidebar.selectbox("Condition / Subgroup", subgroups, index=0, help="Optional condition for the dataset.") if len(subgroups)>1 else subgroups[0]

# Determine base axis semantics/units
base_df = db[selected_material][selected_property][selected_subgroup]
x_col_ref, y_col_ref = choose_xy_columns(base_df)
if x_col_ref is None or y_col_ref is None:
    st.error("Could not infer X/Y columns from the reference dataset.")
    st.stop()
axis_type, base_units = infer_base_x_semantics(x_col_ref)

# ----------------------------------------------------------------------------
# Sidebar: Uploads
# ----------------------------------------------------------------------------
st.sidebar.header("Compare with Your Data")
uploaded_files = st.sidebar.file_uploader("Upload CSV file(s)", type="csv", accept_multiple_files=True, key="file_uploader")

with st.sidebar.expander("Accepted CSV shapes (examples)"):
    st.info("- **2 columns:** `lambda, emissivity`\n- **Grouped/long:** `Curve, T (K), ε, ε_err`\n- **Wide:** `Wavelength, R_s, R_p, R_p_err`")

# Units normalization controls
with st.sidebar.expander("Units normalization", expanded=False):
    st.caption(f"Base X axis appears to be **{axis_type or 'unknown'}** in units **{base_units or '—'}** (derived from reference X label: `{x_col_ref}`).")
    x_input_opt = ["auto (no change)"]
    if axis_type == "temperature":
        x_input_opt += ["Kelvin [K]", "Celsius [°C]"]
    elif axis_type == "wavelength":
        x_input_opt += ["micrometre [µm]", "nanometre [nm]", "wavenumber [cm⁻¹]"]
    elif axis_type == "wavenumber":
        x_input_opt += ["wavenumber [cm⁻¹]", "micrometre [µm]", "nanometre [nm]"]
    selected_x_units = st.selectbox("Uploaded X units", x_input_opt, help="Choose the units of uploaded X data to normalize into the base axis units.")
    y_pct_mode = st.radio("Dimensionless Y: percent → fraction", ["auto", "force", "off"], index=0, horizontal=True, help="Auto scales if values look like percentages (≈ 0–100).")

# Parse uploads
if uploaded_files:
    st.session_state.uploaded_parsed = {}
    base_x_label = x_col_ref or (base_df.columns[1] if base_df.shape[1] >= 2 else "X")
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

# ----------------------------------------------------------------------------
# Main: Reference controls
# ----------------------------------------------------------------------------
header = f"{selected_property} of {selected_material}"
if selected_subgroup != "default": header += f" — Condition: {selected_subgroup}"
st.header(header)

if base_df is None or base_df.empty:
    st.warning("Selected reference dataset is empty.")
    st.stop()

st.subheader("Reference Data Controls")
if "Curve" in base_df.columns:
    all_curves = list(base_df["Curve"].unique())
    selected_curves = st.multiselect("Select reference curves to plot", options=all_curves, default=all_curves)
    ref_df = base_df[base_df["Curve"].isin(selected_curves)] if selected_curves else base_df.iloc[0:0]
else:
    st.info("No 'Curve' column found; plotting the entire reference dataset.")
    ref_df = base_df.copy()

with st.expander("Preview reference data", expanded=False):
    st.caption("Tip: use column menu to sort/filter; this does not affect plotting.")
    st.dataframe(base_df, use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------------
# Plot
# ----------------------------------------------------------------------------
st.subheader("Interactive Comparison Plot")
fig = go.Figure()
any_plotted = False

# Reference
if not ref_df.empty:
    if "Curve" in ref_df.columns:
        for cname, cdf in ref_df.groupby("Curve"):
            fig.add_trace(go.Scatter(x=cdf[x_col_ref], y=cdf[y_col_ref], mode="lines+markers", name=f"{cname} (Ref)"))
    else:
        fig.add_trace(go.Scatter(x=ref_df[x_col_ref], y=ref_df[y_col_ref], mode="lines+markers", name="Reference"))
    any_plotted = True

# Uploaded with normalization
unit_choice_map = {
    "auto (no change)": None,
    "Kelvin [K]": "K",
    "Celsius [°C]": "C",
    "micrometre [µm]": "um",
    "nanometre [nm]": "nm",
    "wavenumber [cm⁻¹]": "cm^-1",
}
chosen_x_input = unit_choice_map.get(selected_x_units, None)

if st.session_state.uploaded_parsed:
    for fname, bundle in st.session_state.uploaded_parsed.items():
        udf, sch = bundle["df"], bundle["schema"]
        mode = sch["mode"]; x = sch["x_col"]; y_cols = sch["y_cols"]
        group_col = sch["group_col"]; y_err, y_minus, y_plus = sch["y_err"], sch["y_minus"], sch["y_plus"]

        # Determine x input units: header-based auto detection if user left 'auto'
        col_units = detect_input_units_from_header(x) if chosen_x_input is None else chosen_x_input

        if mode == "two_col":
            y = y_cols[0]
            # Make a plotting copy with potential normalization
            x_series = convert_x_series(udf[x], col_units, axis_type)
            y_series = udf[y].copy()
            y_err_series = udf[y_err] if y_err and y_err in udf.columns else None
            y_minus_series = udf[y_minus] if y_minus and y_minus in udf.columns else None
            y_plus_series  = udf[y_plus]  if y_plus  and y_plus  in udf.columns else None
            y_series, y_err_series, y_minus_series, y_plus_series = normalize_y_and_errors(y_series, y_err_series, y_minus_series, y_plus_series, y_pct_mode)

            err_kwargs = {}
            if y_minus_series is not None and y_plus_series is not None:
                err_kwargs["error_y"] = dict(
                    type="data",
                    array=(y_plus_series - y_series).abs(),
                    arrayminus=(y_series - y_minus_series).abs(),
                    visible=True,
                )
            elif y_err_series is not None:
                err_kwargs["error_y"] = dict(type="data", array=y_err_series.abs(), visible=True)

            fig.add_trace(go.Scatter(x=x_series, y=y_series, mode="markers", name=os.path.splitext(fname)[0], **err_kwargs))
            any_plotted = True

        elif mode == "grouped":
            y = y_cols[0]
            for g, gdf in udf.groupby(group_col):
                x_series = convert_x_series(gdf[x], col_units, axis_type)
                y_series = gdf[y].copy()
                y_err_series = gdf[y_err] if y_err and y_err in gdf.columns else None
                y_minus_series = gdf[y_minus] if y_minus and y_minus in gdf.columns else None
                y_plus_series  = gdf[y_plus]  if y_plus  and y_plus  in gdf.columns else None
                y_series, y_err_series, y_minus_series, y_plus_series = normalize_y_and_errors(y_series, y_err_series, y_minus_series, y_plus_series, y_pct_mode)

                err_kwargs = {}
                if y_minus_series is not None and y_plus_series is not None:
                    err_kwargs["error_y"] = dict(
                        type="data",
                        array=(y_plus_series - y_series).abs(),
                        arrayminus=(y_series - y_minus_series).abs(),
                        visible=True,
                    )
                elif y_err_series is not None:
                    err_kwargs["error_y"] = dict(type="data", array=y_err_series.abs(), visible=True)

                fig.add_trace(go.Scatter(x=x_series, y=y_series, mode="markers", name=f"{os.path.splitext(fname)[0]} — {g}", **err_kwargs))
            any_plotted = True

        elif mode == "wide":
            for y in y_cols:
                x_series = convert_x_series(udf[x], col_units, axis_type)
                y_series = udf[y].copy()

                # per-series errors
                stem = _clean(y)
                colmap = {c: _clean(c) for c in udf.columns}
                y_minus_cand = next((c for c, cc in colmap.items() if stem in cc and re.search(r"(minus|lower|lo|min)$", cc)), None)
                y_plus_cand  = next((c for c, cc in colmap.items() if stem in cc and re.search(r"(plus|upper|hi|max)$", cc)), None)
                y_err_cand   = next((c for c, cc in colmap.items() if stem in cc and any(k in cc for k in ["err","error","sigma","std","uncert"])), None)

                y_err_series = udf[y_err_cand] if y_err_cand else None
                y_minus_series = udf[y_minus_cand] if y_minus_cand else None
                y_plus_series  = udf[y_plus_cand]  if y_plus_cand  else None

                y_series, y_err_series, y_minus_series, y_plus_series = normalize_y_and_errors(y_series, y_err_series, y_minus_series, y_plus_series, y_pct_mode)

                err_kwargs = {}
                if y_minus_series is not None and y_plus_series is not None:
                    err_kwargs["error_y"] = dict(
                        type="data",
                        array=(y_plus_series - y_series).abs(),
                        arrayminus=(y_series - y_minus_series).abs(),
                        visible=True,
                    )
                elif y_err_series is not None:
                    err_kwargs["error_y"] = dict(type="data", array=y_err_series.abs(), visible=True)

                fig.add_trace(go.Scatter(x=x_series, y=y_series, mode="markers", name=f"{os.path.splitext(fname)[0]} — {y}", **err_kwargs))
            any_plotted = True

# Display plot
if any_plotted:
    fig.update_layout(title="Comparison Plot", xaxis_title=str(x_col_ref), yaxis_title=str(y_col_ref),
                      legend_title="Datasets", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Hover to inspect values; click legend items to isolate/hide series. Use box/lasso tools to zoom.")
else:
    st.info("Select reference curves or upload data to generate a plot.")

# ----------------------------------------------------------------------------
# Upload parsing summary
# ----------------------------------------------------------------------------
if st.session_state.uploaded_parsed:
    st.subheader("Upload Parsing Summary")
    rows = []
    for fname, bundle in st.session_state.uploaded_parsed.items():
        sch = bundle["schema"]
        rows.append({
            "file": fname,
            "mode": sch["mode"],
            "x_col": sch["x_col"],
            "y_cols": ", ".join(sch["y_cols"]),
            "group_col": sch["group_col"] or "",
            "y_err": sch["y_err"] or "",
            "y_minus": sch["y_minus"] or "",
            "y_plus": sch["y_plus"] or "",
            "notes": "; ".join(sch["notes"]) if sch["notes"] else "",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("This table shows how each uploaded file was interpreted (columns, grouping, and error encodings).")

# ----------------------------------------------------------------------------
# Export reference selection
# ----------------------------------------------------------------------------
st.subheader("Data Export")
export_source = ref_df if not ref_df.empty else None
csv_bytes = prepare_csv_export(export_source)
parts = [selected_material, selected_property]
if selected_subgroup != "default": parts.append(selected_subgroup)
safe_filename = "Reference_" + "_".join(p.replace(" ", "_") for p in parts) + ".csv"
if csv_bytes:
    st.download_button("📥 Download Selected Reference Data", data=csv_bytes, file_name=safe_filename, mime="text/csv")
else:
    st.markdown("_Select at least one reference curve (or ensure the dataset is not empty) to enable downloading._")

# ----------------------------------------------------------------------------
# Provenance & Version
# ----------------------------------------------------------------------------
st.subheader("Provenance & Version")
def _git_sha() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
        return sha
    except Exception:
        return "unavailable"

def gather_provenance():
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "streamlit": getattr(st, "__version__", "unknown"),
        "pandas": pd.__version__,
        "plotly": getattr(go, "__version__", "unknown"),
        "git_sha": _git_sha(),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    base = {
        "material": selected_material,
        "property": selected_property,
        "subgroup": selected_subgroup,
        "x_label": x_col_ref,
        "y_label": y_col_ref,
        "axis_type": axis_type,
        "base_units": base_units,
    }
    unit_settings = {
        "uploaded_x_units_choice": selected_x_units,
        "y_percent_mode": y_pct_mode,
    }
    # list reference files discovered
    ref_files = [f for f in sorted(os.listdir("data")) if f.endswith(".csv")]
    uploads = []
    for fname, bundle in st.session_state.get("uploaded_parsed", {}).items():
        sch = bundle["schema"]
        uploads.append({
            "file": fname,
            "schema": sch,
            "n_rows": int(bundle["df"].shape[0]),
            "n_cols": int(bundle["df"].shape[1]),
        })
    return {"environment": env, "base_selection": base, "unit_settings": unit_settings,
            "reference_files": ref_files, "uploads": uploads}

prov = gather_provenance()
st.json(prov, expanded=False)
prov_bytes = io.BytesIO(json.dumps(prov, ensure_ascii=False, indent=2).encode("utf-8"))
st.download_button("📦 Download provenance JSON", data=prov_bytes, file_name="provenance_report.json", mime="application/json",
                   help="Save environment, selections, units settings, and parsing summary for reproducibility.")

# ----------------------------------------------------------------------------
# Documentation tabs (reads docs/*.md)
# ----------------------------------------------------------------------------
st.divider()
st.subheader("Documentation")
def _read_md(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"**Missing file:** `{path}`."
    except Exception as e:
        return f"**Error reading `{path}`:** {e}"

tab_usage, tab_conventions, tab_faq = st.tabs(["Usage Guide", "Data Conventions", "FAQ"])
with tab_usage: st.markdown(_read_md("docs/usage.md"))
with tab_conventions: st.markdown(_read_md("docs/data-conventions.md"))
with tab_faq: st.markdown(_read_md("docs/faq.md"))
