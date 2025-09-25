# Comparative Material Properties Explorer (Streamlit)

This repository contains a Streamlit application for comparative analysis of thermo‑optical reference data (e.g., Chromium, Chromium Oxides) against user‑provided experiments. It features robust CSV schema inference (2‑column, grouped/long, wide), **uncertainty visualization**, optional **units normalization**, and **provenance export**.

> **Note**: Another (“Shony”) app may exist in the repo but is not documented here.

---

## Documentation

- **Usage Guide:** [`docs/usage.md`](docs/usage.md)  
- **Data Conventions:** [`docs/data-conventions.md`](docs/data-conventions.md)  
- **FAQ:** [`docs/faq.md`](docs/faq.md)

---

## Quick start

```bash
python -m pip install --upgrade pip
python -m pip install streamlit pandas plotly
streamlit run app_01_data_import.py
```

Place reference CSVs in `data/` following:
```
<Material>_<Property>[_<Subgroup>].csv
```
e.g., `Chromium_Normal_Total_Emittance.csv`.

---

## Features

- Pickle‑safe caching (`st.cache_data`).
- Strict underscore‑aware filename parsing.
- Upload ingestion for **2‑column**, **grouped/long**, and **wide** tables.
- **Uncertainties**: symmetric and asymmetric error bars.
- **Units normalization**: °C→K, nm→µm, cm⁻¹→µm, percent→fraction (optional).
- Interactive overlays (Plotly) and CSV export of selected reference curves.
- **Provenance export** (JSON): environment, selections, unit settings, parsing summary.

---

## Citation

Please cite the repository (optionally with DOI) and your data sources (e.g., Touloukian handbooks). For reproducibility, record app version (git SHA), reference CSV filenames, and upload filenames/timestamps.

---

## References

1) Touloukian, Y.S. et al. *Thermophysical Properties of Matter* (IFI/Plenum, 1970–1998).  
2) Streamlit — Caching API (`st.cache_data`).  
3) Plotly Graph Objects — Scatter and error bars.
