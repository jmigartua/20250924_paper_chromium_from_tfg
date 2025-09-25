# Usage Guide — Comparative Material Properties Explorer

## 1. Purpose and scope

This application supports **rigorous, reproducible comparison** between curated thermo‑optical reference datasets (e.g., *Chromium*, *Chromium Oxides*) and **user‑provided experimental series**. It emphasizes transparent data ingestion, schema inference (2‑column, grouped “long”, and “wide”), explicit treatment of **measurement uncertainties** (symmetric and asymmetric), and optional **units normalization** for axes and dimensionless quantities [1–4].

## 2. Prerequisites

- Python ≥ 3.10
- Packages: `streamlit`, `pandas`, `plotly`
- A directory `data/` containing reference CSVs named as:
  ```
  <Material>_<Property>[_<Subgroup>].csv
  ```
  e.g., `Chromium_Normal_Total_Emittance.csv`. See the [Data Conventions](./data-conventions.md).

## 3. Installation and execution

```bash
python -m pip install --upgrade pip
python -m pip install streamlit pandas plotly
streamlit run app_01_data_import.py
```

> **Caching.** The app uses `st.cache_data` (pickle‑based). If you previously returned non‑pickleable objects, clear once via `st.cache_data.clear()` and rerun.

## 4. Basic workflow

1. **Select** a *Material*, *Property*, and *Subgroup* (if present).
2. **Inspect** the reference table (Preview) and optionally filter **Curve** labels.
3. **Upload** your CSVs under *Compare with Your Data*. The parser infers one of:
   - **Two‑column**: `X, Y` (headers optional).
   - **Grouped/long**: `Curve/Series, X, Y` with optional `Yerr` *or* `Yminus/Yplus`.
   - **Wide**: one `X` column and **multiple** `Y*` series, with optional per‑series errors.
4. **Normalize units (optional)** via *Units normalization* in the sidebar:
   - Temperature: °C → K (if base axis is in K).
   - Wavelength: nm → µm; or wavenumber (cm⁻¹) → µm via λ(µm)=10⁴/ν(cm⁻¹).
   - Dimensionless Y: percent → fraction.
   The app provides **auto‑detection** (header‑based) with manual overrides.
5. **Compare** overlays interactively (Plotly): hover, zoom, isolate series; export static PNG via Plotly menu.
6. **Export** the selected reference subset via *Download Selected Reference Data*.
7. **Record provenance** via *Provenance & Version* → *Download JSON* (includes environment, selections, unit settings, and parsing summaries).

A *Parsing Summary* table documents how each upload was interpreted (chosen columns, grouping, error encodings) for auditability.

## 5. Uncertainty handling

- **Symmetric errors**: columns whose cleaned name contains `err`, `error`, `sigma`, `std`, or `uncertainty` are rendered as ±σ about *Y*.
- **Asymmetric errors**: pairs with suffixes like `minus/lower/lo/min` and `plus/upper/hi/max` are used to form (*Y*−, *Y*+) intervals.
- For **wide** tables, the app attempts per‑series pairing (e.g., `R_p` with `R_p_err` or `R_p_lower/R_p_upper`).

## 6. Axis and property semantics

The upload parser biases:
- **X** toward the current reference axis (e.g., `T (K)` → *temperature*, *t*, *k*; `λ (µm)` → *wavelength*, *lambda*, *wl*; or **wavenumber** when applicable).
- **Y** toward the selected property family (e.g., *Emissivity/Emittance*, *Reflectance*, *Absorptance*, *Transmittance*).

If inference is ambiguous, the app falls back to the first two numeric columns (or the first two columns as a last resort), and notes this in *Parsing Summary*.

## 7. Reproducibility and provenance

- The app returns **plain dicts and DataFrames** from cacheable paths (no anonymous callables), ensuring stability under pickle serialization.
- Use *Provenance & Version* → *Download JSON* to capture:
  - app/git version (if available), Python and library versions;
  - base dataset selection; unit settings;
  - list of reference files and uploaded files with inferred schemas.
- For publications, record the exact dataset filenames and timestamps [1,5].

## 8. Troubleshooting

- **No reference data found.** Verify `data/` exists and filenames adhere to the convention.
- **Upload not recognized.** Consult *Parsing Summary*. Consider renaming columns to include informative tokens (e.g., `T (K)`, `λ (µm)`, `emissivity`, `reflectance`, `err`).
- **Cache stale.** Clear once with `st.cache_data.clear()` and rerun.
- **Units mismatch.** Enable the *Units normalization* controls and/or standardize headers/units.

---

## References

[1] Touloukian, Y.S. et al. *Thermophysical Properties of Matter* (IFI/Plenum, 1970–1998).  
[2] Modest, M.F. *Radiative Heat Transfer* (Academic Press, 2013).  
[3] Incropera, F.P. et al. *Fundamentals of Heat and Mass Transfer* (Wiley, 2007).  
[4] Nicodemus, F.E. et al. “Geometrical Considerations and Nomenclature for Reflectance.” *NBS Monograph* 160 (1977).  
[5] Peng, R.D. “Reproducible Research in Computational Science.” *Science* 334, 1226–1227 (2011).
