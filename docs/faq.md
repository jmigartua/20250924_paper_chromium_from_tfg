# FAQ — Comparative Material Properties Explorer

**Q1. My upload did not plot. What should I check?**  
A1. Open *Upload Parsing Summary* to see what the parser inferred. Ensure you have (i) at least two columns, (ii) numeric *X* and *Y*, and (iii) informative headers (e.g., `T (K)`, `λ (µm)`, `emissivity`, `reflectance`, `err`). For **wide** tables, confirm per‑series error columns share a stem with the *Y* they belong to (e.g., `R_p` with `R_p_err`).

**Q2. How do I add a new material/property?**  
A2. Edit `KNOWN_MATERIALS` / `KNOWN_PROPERTIES` in `app_01_data_import.py`. Reference filenames must use the underscore form of the property (e.g., `Normal_Total_Emittance`).

**Q3. Can the app convert units (e.g., °C→K, nm→µm, cm⁻¹→µm)?**  
A3. Yes, enable *Units normalization* in the sidebar. The app also attempts header‑based auto‑detection, but manual overrides are provided.

**Q4. What about percentage values in Y?**  
A4. Enable *Percent → fraction* to divide Y by 100 (symmetric/asymmetric errors are scaled accordingly).

**Q5. How do I clear cache?**  
A5. Run once: `st.cache_data.clear()` (inside the app or a temp script). Then restart Streamlit.

**Q6. How should I cite this tool and data?**  
A6. Cite the repository (optionally with a DOI if minted), and underlying data sources (e.g., Touloukian handbooks). Include app version (git SHA), reference CSV names, and upload filenames/timestamps.

**Q7. Performance tips?**  
A7. Prefer narrow CSVs (only necessary columns), avoid excessively large wide tables, and consider pre‑aggregating or down‑sampling for very dense spectra.

**Q8. Privacy?**  
A8. Uploaded files are processed locally in your Streamlit session; no network transmission is performed by this app.

---

## References

[1] Streamlit — *Caching API (`st.cache_data`)*.  
[2] Plotly Graph Objects — *Scatter traces and error bars*.  
[3] Peng, R.D. “Reproducible Research in Computational Science.” *Science* 334, 1226–1227 (2011).
