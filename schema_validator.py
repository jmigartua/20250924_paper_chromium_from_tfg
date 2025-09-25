from __future__ import annotations
import re, pandas as pd

def _clean(s: str) -> str:
    if s is None: return ""
    x = re.sub(r"\([^)]*\)", "", s)
    greek_map = {"ε": "epsilon", "λ": "lambda", "ρ": "rho", "α": "alpha", "τ": "tau"}
    for g,a in greek_map.items():
        x = x.replace(g, a)
    x = re.sub(r"[^a-zA-Z0-9]+", "_", x.lower()).strip("_")
    return x

def _tokens(s: str): return [t for t in _clean(s).split("_") if t]
def _similar(a: str, b: str) -> float:
    ta, tb = set(_tokens(a)), set(_tokens(b))
    return 0.0 if not ta or not tb else len(ta & tb)/len(ta | tb)

def _find_column_by_synonyms(df, synonyms):
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

def _first_two_numeric(df):
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    return (num[0], num[1]) if len(num) >= 2 else (None, None)

def _x_synonyms(base_x_label: str):
    bx = (base_x_label or "").lower()
    syn = ["x"]
    if "temp" in bx or "(k)" in bx or bx.strip() in {"t", "t k"}:
        syn += ["t", "temperature", "temp", "t_k", "k"]
    if "wave" in bx or "lambda" in bx or "lam" in bx or "µm" in bx or "um" in bx:
        syn += ["wavelength", "lambda", "lam", "wl", "micron", "um", "µm"]
    if "wavenumber" in bx or "cm" in bx:
        syn += ["wavenumber", "1_cm", "cm_1", "k", "nu"]
    return syn

def _y_synonyms(selected_property: str):
    p = (selected_property or "").lower()
    syn = []
    if "emiss" in p: syn += ["emissivity", "emittance", "epsilon", "eps"]
    if "reflect" in p: syn += ["reflectance", "rho", "r"]
    if "absorpt" in p: syn += ["absorptance", "alpha", "a"]
    if "transmit" in p: syn += ["transmittance", "tau", "t"]
    syn += ["y", "intensity", "signal", "value"]
    return syn

def _detect_error_columns(df, y_col):
    cols = list(df.columns)
    yc = _clean(y_col)
    minus = [c for c in cols if re.search(r"(minus|lower|lo|min)$", _clean(c))]
    plus  = [c for c in cols if re.search(r"(plus|upper|hi|max)$", _clean(c))]
    y_minus = next((c for c in minus if _similar(_clean(c), yc) >= 0.34), None)
    y_plus  = next((c for c in plus  if _similar(_clean(c), yc) >= 0.34), None)
    if y_minus and y_plus: return None, y_minus, y_plus
    err_names = ["err","error","sigma","std","stderr","uncert","uncertainty"]
    cands = [c for c in cols if any(n in _clean(c) for n in err_names)]
    cands.sort(key=lambda c: _similar(_clean(c), yc), reverse=True)
    if cands: return cands[0], None, None
    if "err" in [c.lower() for c in cols]: return "err", None, None
    return None, None, None

def infer_schema(df, base_x_label, selected_property):
    cols = list(df.columns)
    group_candidates = ["curve","series","label","group","dataset","name"]
    group_col = _find_column_by_synonyms(df, group_candidates)

    x_col = _find_column_by_synonyms(df, _x_synonyms(base_x_label))
    y_col = _find_column_by_synonyms(df, _y_synonyms(selected_property))
    if x_col is None:
        x_col, _ = _first_two_numeric(df)
    if y_col is None:
        num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and c != x_col]
        if num: y_col = num[0]
    if x_col is None or y_col is None:
        return dict(mode="invalid", x_col=x_col, y_cols=[], group_col=group_col, y_err=None, y_minus=None, y_plus=None)

    other_numeric = [c for c in cols if c != x_col and pd.api.types.is_numeric_dtype(df[c])]
    if not group_col and len(other_numeric) >= 2:
        err_kw = ("err","error","sigma","std","uncert")
        y_cols = [c for c in other_numeric if not any(k in _clean(c) for k in err_kw)] or other_numeric[:1]
        return dict(mode="wide", x_col=x_col, y_cols=y_cols, group_col=None, y_err=None, y_minus=None, y_plus=None)

    if group_col:
        y_err,y_minus,y_plus = _detect_error_columns(df, y_col)
        return dict(mode="grouped", x_col=x_col, y_cols=[y_col], group_col=group_col, y_err=y_err, y_minus=y_minus, y_plus=y_plus)

    y_err,y_minus,y_plus = _detect_error_columns(df, y_col)
    return dict(mode="two_col", x_col=x_col, y_cols=[y_col], group_col=None, y_err=y_err, y_minus=y_minus, y_plus=y_plus)
