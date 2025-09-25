# Data Conventions and File Formats

## 1. Directory structure

```
project/
├─ app_01_data_import.py
└─ data/
   ├─ Chromium_Hemispherical_Total_Emittance.csv
   ├─ Chromium_Normal_Total_Emittance.csv
   └─ ...
```

## 2. Reference file naming

```
<Material>_<Property>[_<Subgroup>].csv
```

- `Material` ∈ `{Chromium, ChromiumOxides}` (extendable).
- `Property` uses underscores and maps to display names:
  - `Hemispherical_Total_Emittance`
  - `Normal_Total_Emittance`
  - `Normal_Spectral_Emittance`
  - `Normal_Spectral_Reflectance`
  - `Angular_Spectral_Reflectance`
  - `Normal_Spectral_Absorptance`
  - `Normal_Solar_Absorptance`
  - `Normal_Spectral_Transmittance`
- `Subgroup` is optional, free‑form (e.g., `Annealed`, `Polished_873K`).

## 3. Reference CSV column expectations

Two supported layouts:

**(a) With Curve labels (preferred for multi‑series)**  
```
Curve, X, Y, [optional extra columns]
```
Examples:
- `Curve, T (K), Emittance`
- `Curve, λ (µm), ρ(λ)`

**(b) Minimal numeric layout**  
- At least **two numeric** columns. The app uses the first two numeric columns as *(X, Y)* if no `Curve` is present.

> **Recommendation.** Use explicit units in parentheses in headers (e.g., `T (K)`, `λ (µm)`), even if units are constant.

## 4. Upload CSV shapes

**Two‑column**  
```
X, Y
```
Headers optional; first two numeric columns are used if headers are absent or ambiguous.

**Grouped / long**  
```
Curve|Series|Label, X, Y, [Yerr | (Yminus,Yplus)]
```
- `Curve/Series/Label`: series identifier.
- Optional symmetric error (`Yerr`) or asymmetric bounds (`Yminus`, `Yplus`).

**Wide**  
```
X, Y1, Y2, ..., [Y1_err | Y1_lower/Y1_upper], ...
```
- One X column shared by multiple Y series.
- Per‑series error columns are associated by **stem matching** (e.g., `R_p` ↔ `R_p_err`).

## 5. Uncertainty encodings

- **Symmetric**: a column whose cleaned name contains `err`, `error`, `sigma`, `std`, or `uncertainty` → rendered as ±σ about *Y*.  
- **Asymmetric**: columns whose cleaned names end with `minus/lower/lo/min` and `plus/upper/hi/max` (paired to the stem of *Y*) → rendered as (*Y*−, *Y*+).

## 6. Units and dimensional consistency

- The app can **normalize** common axis units:
  - Temperature: °C → **K** (if base axis in K).
  - Wavelength: **nm** → **µm**; wavenumber (**cm⁻¹**) → **µm** using λ(µm)=10⁴/ν(cm⁻¹).
  - Dimensionless Y: **percent** → **fraction** (×0.01).
- If units are already consistent, leave normalization **off** to avoid accidental re‑scaling.

## 7. Extending materials and properties

- Add a new material to `KNOWN_MATERIALS` in `app_01_data_import.py`.
- Add a new property (display name) to `KNOWN_PROPERTIES` and ensure filenames use the underscore form of that name.

---

## References

[1] Touloukian, Y.S. et al. *Thermophysical Properties of Matter* (IFI/Plenum, 1970–1998).  
[2] Nicodemus, F.E. et al. “Geometrical Considerations and Nomenclature for Reflectance.” *NBS Monograph* 160 (1977).
