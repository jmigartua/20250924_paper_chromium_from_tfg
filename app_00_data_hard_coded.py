import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# ==============================================================================
# PHASE 1: DATA PREPARATION AND STRUCTURING
# All data from the markdown files is transcribed into a structured
# Python dictionary with Pandas DataFrames.
# ==============================================================================

def build_database():
    """
    Creates the main nested dictionary containing all material property data.
    This function isolates the data definition from the application logic.
    """
    database = {
        "Chromium": {
            "Hemispherical Total Emittance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1], 'Ref. No.': [9], 'Year': [1960], 'Temperature Range, K': [77.4], 'Reported Error, %': [None],
                    'Composition (weight percent), Specifications and Remarks': ['Plated on monel; measured in vacuum (10⁻⁵ mm Hg).']
                }),
                "data_table_info": "[Temperature, T, K; Emittance, ∈]",
                "curves": {
                    "Curve 1*": pd.DataFrame({'T': [77.4], '∈': [0.084]})
                }
            },
            "Normal Total Emittance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1, 2, 3, 4, 5],
                    'Ref. No.': [16, 15, 34, 34, 34],
                    'Year': [1937, 1947, 1957, 1957, 1957],
                    'Temperature Range, K': ['367', '373', '516-1005', '680-1216', '722-1205'],
                    'Reported Error, %': ['±1.1', None, '±10', '±10', '±10'],
                    'Remarks': [
                        'Plated on iron; polished.',
                        'Polished.',
                        'Pure; strip (0.005 in. thick); same results obtained for 4 different surface treatments; measured in air; increasing temp, Cycle 1.',
                        'Above specimen and conditions, Cycle 2.',
                        'Above specimen and conditions, Cycle 3.'
                    ]
                }),
                "data_table_info": "[Temperature, T, K; Emittance, E]",
                "curves": {
                    "Curve 1": pd.DataFrame({'T': [367], 'E': [0.08]}),
                    "Curve 2": pd.DataFrame({'T': [373], 'E': [0.075]}),
                    "Curve 3": pd.DataFrame({'T': [516, 903, 1005], 'E': [0.055, 0.141, 0.230]}),
                    "Curve 4": pd.DataFrame({'T': [680, 855, 966, 1072, 1166, 1216], 'E': [0.110, 0.171, 0.240, 0.405, 0.382, 0.420]}),
                    "Curve 5": pd.DataFrame({'T': [722, 905, 1072, 1205], 'E': [0.290, 0.355, 0.435, 0.480]})
                }
            },
            "Normal Spectral Emittance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1, 2, '1_b'], # Using unique keys for different tables
                    'Ref. No.': [19, 39, 19],
                    'Year': [1914, 1948, 1914],
                    'Wavelength/Range, μ': ['0.65', '0.669', '0.55-0.65'],
                    'Temperature/Range, K': ['1703', '1550', '1733'],
                    'Remarks': [
                        'Film; tungsten substrate; melted in H₂ then oxidized in air; Pt reference.',
                        'Heated in H₂ for one week at 1493 K; measured in H₂; independent of temp up to 1550 K.',
                        'Film; tungsten substrate; measured in H₂; Pt reference.'
                    ]
                }),
                "data_table_info": "[Wavelength, λ, μ; Emittance, E; Temperature, T, K]",
                "curves": {
                    "Curve 1 (T=1703K, λ=0.65μ)": pd.DataFrame({'T': [1703], 'E': [0.60]}),
                    "Curve 2 (T=1550K, λ=0.669μ)": pd.DataFrame({'T': [1550], 'E': [0.334]}),
                    "Curve 3 (T=1733K)": pd.DataFrame({'λ': [0.55, 0.65], 'E': [0.53, 0.39]})
                }
            },
            "Normal Spectral Reflectance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1, 2, 3, 4, 5, 6],
                    'Ref. No.': [124, 146, 223, 223, 223, 235],
                    'Year': [1941, 1958, 1962, 1962, 1962, 1967],
                    'Temperature K': [298, 298, 298, 298, 77, 298],
                    'Wavelength Range, μ': ['0.13-0.20', '0.3-2.7', '2.0-26.0', '2.0-26.0', '2.0-26.0', '2.5-30.0'],
                    'Remarks': [
                        'Polished; measured in vacuum.',
                        'Electroplated; data from smooth curve; MgCO₃ ref.',
                        'Polished; converted from R(2π, 0°).',
                        'Above specimen and conditions except after particle impact.',
                        'Above specimen and conditions.',
                        '5N pure chromium; mechanically polished; electro-polished; annealed.'
                    ]
                }),
                "data_table_info": "[Wavelength, λ, μ; Reflectance, p]",
                "curves": {
                    "Curve 1 (T=298K)": pd.DataFrame({'λ': [0.1347, 0.1438, 0.1570, 0.1640, 0.1757, 0.1901, 0.2026], 'p': [0.14, 0.16, 0.19, 0.22, 0.27, 0.32, 0.37]}),
                    "Curve 2 (T=298K)": pd.DataFrame({'λ': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7], 'p': [0.485, 0.570, 0.589, 0.570, 0.565, 0.577, 0.587, 0.572, 0.580, 0.600, 0.633, 0.672, 0.681, 0.681, 0.673, 0.674, 0.700, 0.730, 0.764, 0.790, 0.826, 0.845, 0.890, 0.927, 0.905]}),
                    "Curve 3 (T=298K)": pd.DataFrame({'λ': [2.00, 2.73, 4.07, 6.41, 8.50, 10.87, 12.51, 14.18, 17.60, 21.94, 25.99], 'p': [0.780, 0.844, 0.902, 0.943, 0.942, 0.950, 0.949, 0.946, 0.946, 0.948, 0.953]}),
                    "Curve 4 (T=298K)": pd.DataFrame({'λ': [2.00, 2.61, 3.89, 5.31, 7.49, 9.31, 11.33, 13.49, 15.57, 18.79, 21.53, 23.57, 26.00], 'p': [0.728, 0.788, 0.849, 0.881, 0.900, 0.904, 0.906, 0.915, 0.921, 0.923, 0.930, 0.925, 0.909]}),
                    "Curve 5 (T=77K)": pd.DataFrame({'λ': [2.00, 3.89, 5.98, 7.99, 9.94, 11.99, 13.98, 16.02, 18.02, 20.05, 21.90, 23.98, 26.00], 'p': [0.727, 0.864, 0.906, 0.913, 0.903, 0.901, 0.922, 0.922, 0.925, 0.924, 0.930, 0.913, 0.909]}),
                    "Curve 6* (T=298K)": pd.DataFrame({'λ': [2.5, 3.0, 4.0, 5.0, 6.0, 6.4, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 20.0, 25.0, 30.0], 'p': [0.709, 0.778, 0.848, 0.879, 0.890, 0.900, 0.915, 0.927, 0.938, 0.946, 0.955, 0.960, 0.964, 0.969, 0.972, 0.975, 0.976, 0.977]})
                }
            },
            "Angular Spectral Reflectance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1], 'Ref. No.': [132], 'Year': [1911], 'Temperature K': [298], 'Wavelength Range, μ': ['0.55-9.40'],
                    'Remarks': ['Polished; silvered glass mirror reference.']
                }),
                "data_table_info": "[Wavelength, λ, μ; Reflectance, ρ]",
                "curves": {
                    "Curve 1 (T=298K)": pd.DataFrame({'λ': [0.55, 1.17, 1.55, 2.05, 2.45, 3.05, 4.05, 4.80, 5.45, 6.10, 6.60, 7.10, 7.50, 8.10, 8.45, 8.80, 9.40], 'ρ': [0.550, 0.575, 0.605, 0.623, 0.650, 0.700, 0.765, 0.795, 0.825, 0.855, 0.860, 0.870, 0.875, 0.885, 0.900, 0.903, 0.920]})
                }
            },
            "Normal Spectral Absorptance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1], 'Ref. No.': [307], 'Year': [1954], 'Temperature K': ['~298'], 'Wavelength Range, μ': ['0.400-2.600'],
                    'Remarks': ['Polished; data extracted from smooth curve.']
                }),
                "data_table_info": "[Wavelength, λ, μ; Absorptance, α]",
                "curves": {
                    "Curve 1 (T=~298K)": pd.DataFrame({'λ': [0.400, 0.451, 0.708, 0.801, 1.057, 1.193, 1.481, 1.596, 1.684, 1.800, 2.000, 2.200, 2.400, 2.600], 'α': [0.351, 0.343, 0.379, 0.368, 0.352, 0.313, 0.317, 0.298, 0.298, 0.265, 0.238, 0.200, 0.163, 0.169]})
                }
            },
            "Normal Solar Absorptance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': [1, 2], 'Ref. No.': [146, 146], 'Year': [1958, 1958], 'Temperature K': [298, 298],
                    'Remarks': [
                        'Electroplated; computed from spectral reflectivity for sea level conditions.',
                        'Electroplated; computed from spectral reflectivity for above atmosphere conditions.'
                    ]
                }),
                "data_table_info": "[Temperature, T, K; Absorptance, α]",
                "curves": {
                    "Curve 1* (Sea Level)": pd.DataFrame({'T': [298], 'α': [0.415]}),
                    "Curve 2* (Above Atmosphere)": pd.DataFrame({'T': [298], 'α': [0.397]})
                }
            },
            "Normal Spectral Transmittance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': range(1, 10),
                    'Remarks': [
                        'Evaporated film (optical thickness 334 Å); evaporated onto glass microscope slide.',
                        'Different sample, same conditions except optical thickness 457 Å.',
                        'Different sample, same conditions except optical thickness 573 Å.',
                        'Different sample, same conditions except optical thickness 695 Å.',
                        'Different sample, same conditions except optical thickness 829 Å.',
                        'Different sample, same conditions except optical thickness 935 Å.',
                        'Different sample, same conditions except optical thickness 983 Å.',
                        'Different sample, same conditions except optical thickness 1072 Å.',
                        'Different sample, same conditions except optical thickness 1134 Å.'
                    ]
                }),
                "data_table_info": "[Wavelength, λ, μ; Transmittance, τ]",
                "curves": {
                    "Curve 1 (T=298K, 334Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.438]}),
                    "Curve 2 (T=298K, 457Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.309]}),
                    "Curve 3 (T=298K, 573Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.240]}),
                    "Curve 4 (T=298K, 695Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.206]}),
                    "Curve 5 (T=298K, 829Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.134]}),
                    "Curve 6 (T=298K, 935Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.092]}),
                    "Curve 7 (T=298K, 983Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.082]}),
                    "Curve 8 (T=298K, 1072Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.057]}),
                    "Curve 9 (T=298K, 1134Å)": pd.DataFrame({'λ': [0.546], 'τ': [0.048]})
                }
            }
        },
        "Chromium Oxides": {
            "Normal Total Emittance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': ['1*', '2*', '3*', '4*'],
                    'Ref. No.': [28, 200, 362, 362],
                    'Year': [1963, 1962, 1964, 1964],
                    'Temperature Range, K': ['1023', '1273', '873-1273', '873-1273'],
                    'Remarks': [
                        'Cr₂O₃; sintered at 2173 K for 2 hrs; integrated from spectral data.',
                        'Cr₂O₃; 99.5 pure; 1.3 mm thick plate; sintered at 2123 K for 2 hrs.',
                        'Cr₂O₃; 99.5 pure powder, McGean Chemical Co.; sintered 2 hrs at 2173 K.',
                        'Cr₂O₃; similar to above but calculated from spectral data.'
                    ]
                }),
                "data_table_info": "[Temperature, T, K; Emittance, E]",
                "curves": {
                    "Curve 1": pd.DataFrame({'T': [1023], 'E': [0.91]}),
                    "Curve 2": pd.DataFrame({'T': [1273], 'E': [0.69]}),
                    "Curve 3": pd.DataFrame({'T': [873, 1073, 1273], 'E': [0.85, 0.90, 0.80]}),
                    "Curve 4": pd.DataFrame({'T': [873, 1073, 1273], 'E': [0.86, 0.91, 0.82]})
                }
            },
            "Normal Spectral Emittance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': range(1, 10), 'Year': [1962, 1963, 1965, 1965, 1965, 1964, 1964, 1964, 1966],
                    'Temperature K': [1273, 1023, 1273, 1273, 1273, 878, 1073, 1273, 1273],
                    'Remarks': [
                        'Cr₂O₃; 99.5 pure plate.', 'Cr₂O₃; sintered, density 3.15 g/cm³.',
                        'Cr₂O₃; sintered 15 hrs at 1273 K, density 2.05.', 'Above, sintered more, density increased to 2.87.',
                        'Above, sintered more, density decreased to 2.23.', 'Cr₂O₃; 99.5 pure powder.',
                        'Above specimen and conditions.', 'Above specimen and conditions.',
                        'Cr₂O₃; cold pressed and sintered with polyvinyl binder.'
                    ]
                }),
                "data_table_info": "[Wavelength, λ, μm; Emittance, E]",
                "curves": {
                    "Curve 1 (T=1273K)": pd.DataFrame({'λ': [1.00, 1.30, 1.60, 1.90, 3.00, 3.60, 4.00, 4.20, 4.30, 4.40, 6.00, 6.80, 7.60, 8.00, 8.60, 9.00, 10.0, 10.2, 10.4, 11.8, 13.2, 14.0, 14.7, 15.0], 'E': [0.760, 0.660, 0.640, 0.675, 0.675, 0.685, 0.690, 0.670, 0.665, 0.675, 0.685, 0.710, 0.750, 0.775, 0.800, 0.825, 0.845, 0.860, 0.880, 0.890, 0.910, 0.920, 0.815, 0.780]}),
                    "Curve 2 (T=1023K)": pd.DataFrame({'λ': [1.00, 1.16, 1.50, 1.78, 1.92, 2.10, 2.38, 2.54, 2.62, 2.96, 3.16, 3.79, 4.16, 4.27, 4.50, 4.62, 5.62, 5.72, 5.88, 6.52, 6.65, 6.72, 6.99, 7.98, 8.13, 8.43, 8.74, 8.80, 8.88, 8.98, 9.26, 9.50, 10.0, 10.5, 11.5, 12.7, 12.8, 13.0, 13.4, 13.8, 14.0, 14.2, 14.4, 14.7, 14.9, 15.0], 'E': [0.885, 0.835, 0.816, 0.846, 0.881, 0.905, 0.922, 0.922, 0.900, 0.913, 0.947, 0.952, 0.965, 0.930, 0.927, 0.937, 0.924, 0.935, 0.921, 0.927, 0.938, 0.922, 0.931, 0.931, 0.899, 0.911, 0.911, 0.922, 0.896, 0.915, 0.915, 0.906, 0.923, 0.938, 0.948, 0.955, 0.965, 0.956, 0.968, 0.973, 0.962, 0.950, 0.945, 0.907, 0.896, 0.915]}),
                    "Curve 3 (T=1273K)": pd.DataFrame({'λ': [1.00, 5.05, 5.99, 7.00, 9.37, 10.3, 12.7, 13.7, 14.2, 14.6, 15.0], 'E': [0.671, 0.706, 0.706, 0.761, 0.880, 0.908, 0.957, 0.954, 0.933, 0.879, 0.828]}),
                    "Curve 4 (T=1273K)": pd.DataFrame({'λ': [1.00, 5.46, 6.77, 7.83, 9.31, 10.3, 12.7, 13.7, 14.2, 14.6, 15.0], 'E': [0.726, 0.749, 0.765, 0.805, 0.879, 0.908, 0.957, 0.954, 0.933, 0.879, 0.828]}),
                    "Curve 5 (T=1273K)": pd.DataFrame({'λ': [1.00, 4.81, 5.90, 6.87, 7.55, 9.18, 10.1, 11.0, 12.8, 13.3, 14.0, 14.5, 15.0], 'E': [0.763, 0.767, 0.770, 0.799, 0.848, 0.912, 0.944, 0.966, 0.991, 0.994, 0.979, 0.948, 0.897]}),
                    "Curve 6 (T=878K)": pd.DataFrame({'λ': [1.00, 1.40, 2.01, 2.76, 3.11, 6.46, 8.11, 10.4, 12.1, 13.2, 13.6, 13.8, 14.1, 14.6, 14.7, 15.0], 'E': [0.779, 0.798, 0.810, 0.823, 0.841, 0.890, 0.900, 0.923, 0.925, 0.940, 0.937, 0.926, 0.892, 0.805, 0.784, 0.769]}),
                    "Curve 7 (T=1073K)": pd.DataFrame({'λ': [1.00, 2.00, 2.63, 5.12, 6.44, 7.41, 8.54, 12.7, 14.0, 14.2, 14.5, 14.7, 15.0], 'E': [0.863, 0.867, 0.889, 0.907, 0.913, 0.926, 0.926, 0.973, 0.980, 0.953, 0.901, 0.875, 0.856]}),
                    "Curve 8 (T=1273K)": pd.DataFrame({'λ': [1.00, 1.97, 3.11, 6.43, 8.11, 10.4, 11.9, 12.2, 13.3, 13.7, 13.9, 14.4, 14.9, 15.0], 'E': [0.735, 0.778, 0.841, 0.882, 0.900, 0.924, 0.940, 0.947, 0.954, 0.962, 0.963, 0.926, 0.873, 0.856]}),
                    "Curve 9 (T=1273K)": pd.DataFrame({'λ': [1.00, 2.28, 3.16, 4.61, 5.53, 6.08, 6.86, 8.14, 8.77, 9.56, 11.6, 13.3, 14.1, 14.3, 14.6, 15.0], 'E': [0.670, 0.672, 0.674, 0.667, 0.671, 0.685, 0.719, 0.777, 0.803, 0.830, 0.879, 0.904, 0.918, 0.911, 0.877, 0.817]})
                }
            },
            "Normal Spectral Reflectance": {
                "spec_table": pd.DataFrame({
                    'Curve No.': ['1', '2', '3*', '4', '5', '6*', '7'],
                    'Remarks': [
                        'Cr₂O₃; sintered at 2173 K.',
                        'Cr₂O₃; 99.5 pure powder, compacted at 11500 psi.',
                        'Similar to above, compacted at 23200 psi.',
                        'Similar to above, compacted at 34600 psi.',
                        'CrO₂; 99.6 pure powder, compacted at 11500 psi.',
                        'Similar to above, compacted at 23200 psi.',
                        'Similar to above, compacted at 34600 psi.'
                    ]
                }),
                "data_table_info": "[Wavelength, λ, μm; Reflectance, p]",
                "curves": {
                    "Curve 1 (T=298K)": pd.DataFrame({'λ': [0.230, 0.259, 0.278, 0.326, 0.350, 0.421, 0.649, 0.850, 1.15, 1.65, 1.97, 2.35, 2.65], 'p': [0.090, 0.080, 0.088, 0.080, 0.080, 0.067, 0.064, 0.070, 0.065, 0.065, 0.068, 0.072, 0.075]}),
                    "Curve 2 (T~298K)": pd.DataFrame({'λ': [0.230, 0.280, 0.374, 0.579, 0.748, 0.828, 1.35, 1.99, 2.65], 'p': [0.081, 0.058, 0.081, 0.112, 0.300, 0.496, 0.458, 0.467, 0.489]}),
                    "Curve 3 (T~298K)": pd.DataFrame({'λ': [0.230, 0.280, 0.381, 0.481, 0.598, 0.805, 1.08, 1.65, 2.27, 2.65], 'p': [0.081, 0.059, 0.072, 0.100, 0.122, 0.477, 0.461, 0.440, 0.459, 0.473]}),
                    "Curve 4 (T~298K)": pd.DataFrame({'λ': [0.230, 0.280, 0.377, 0.484, 0.674, 0.808, 1.05, 1.45, 2.05, 2.65], 'p': [0.070, 0.045, 0.067, 0.145, 0.201, 0.469, 0.451, 0.428, 0.444, 0.464]}),
                    "Curve 5 (T~298K)": pd.DataFrame({'λ': [0.230, 0.291, 0.383, 0.560, 0.739, 0.966, 1.16, 1.34, 1.82, 2.27, 2.65], 'p': [0.094, 0.101, 0.082, 0.094, 0.173, 0.668, 0.814, 0.815, 0.717, 0.579, 0.337]}),
                    "Curve 6 (T~298K)": pd.DataFrame({'λ': [0.230, 0.299, 0.368, 0.570, 0.772, 0.985, 1.19, 1.38, 1.80, 2.09, 2.44, 2.65], 'p': [0.092, 0.098, 0.077, 0.095, 0.209, 0.668, 0.804, 0.778, 0.699, 0.596, 0.400, 0.283]}),
                    "Curve 7 (T~298K)": pd.DataFrame({'λ': [0.230, 0.309, 0.415, 0.537, 0.753, 0.991, 1.19, 1.37, 1.51, 1.84, 2.11, 2.40, 2.65], 'p': [0.090, 0.093, 0.104, 0.090, 0.180, 0.599, 0.661, 0.638, 0.615, 0.573, 0.517, 0.399, 0.266]})
                }
            }
        }
    }
    return database

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def parse_data_table_info(info_string):
    """
    Parses the info string to extract axis labels.
    Assumes the format is "[X_label, X_symbol, X_unit; Y_label, Y_symbol, Y_unit]"
    """
    try:
        parts = info_string.strip("[]").split(';')
        x_parts = parts[0].split(',')
        y_parts = parts[1].split(',')
        
        x_label = f"{x_parts[0].strip()}, {x_parts[1].strip()} ({x_parts[2].strip()})"
        y_label = f"{y_parts[0].strip()}, {y_parts[1].strip()}"
        
        return x_label, y_label
    except Exception:
        # Fallback for simpler or unexpected formats
        try:
            parts = info_string.strip("[]").split(';')
            return parts[0].strip(), parts[1].strip()
        except Exception:
            return "X-Axis", "Y-Axis"

def prepare_csv_export(dataframes_dict, selected_keys):
    """
    Combines selected dataframes into a single CSV string for download.
    """
    dfs_to_export = []
    for key in selected_keys:
        if key in dataframes_dict:
            df = dataframes_dict[key].copy()
            df['Curve'] = key
            # Reorder columns to have 'Curve' first
            cols = ['Curve'] + [col for col in df if col != 'Curve']
            dfs_to_export.append(df[cols])
    
    if not dfs_to_export:
        return None
        
    # Concatenate all dataframes
    export_df = pd.concat(dfs_to_export, ignore_index=True)
    
    # Convert to CSV string in-memory
    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    
    return csv_buffer.getvalue().encode('utf-8')

# ==============================================================================
# STREAMLIT APP LAYOUT AND LOGIC
# ==============================================================================

# --- Page Configuration ---
st.set_page_config(
    page_title="Material Properties Explorer",
    layout="wide"
)

# --- Load Data ---
db = build_database()

# --- App Title ---
st.title("Interactive Material Properties Explorer")
st.markdown("An application to visualize and export thermal radiative property data for Chromium and its oxides.")

# --- Sidebar for Navigation ---
st.sidebar.header("Navigation")

selected_material = st.sidebar.radio(
    "Select Material",
    list(db.keys())
)

# Dynamically populate properties based on selected material
material_properties = list(db[selected_material].keys())
selected_property = st.sidebar.selectbox(
    "Select Property",
    material_properties
)

# --- Main Content Display ---
st.header(f"{selected_property} of {selected_material}")

# Retrieve the selected data object
property_data = db[selected_material][selected_property]

# Display Specification Table in an expander
with st.expander("View Specification Details"):
    st.markdown("The following table provides context on sample preparation, measurement conditions, and data sources.")
    # Use st.dataframe for better presentation of Pandas DataFrame
    st.dataframe(property_data["spec_table"], use_container_width=True)

# Interactive Curve Selection
st.subheader("Interactive Plot")

available_curves = list(property_data["curves"].keys())

# Let user select which curves to plot
selected_curves = st.multiselect(
    "Select curves to plot:",
    options=available_curves,
    default=available_curves
)

# --- Plotting and Export Logic ---
if not selected_curves:
    st.warning("Please select at least one curve to display the plot.")
else:
    # 1. Create and display the Plotly figure
    fig = go.Figure()
    
    # Get axis labels
    x_label, y_label = parse_data_table_info(property_data["data_table_info"])

    for curve_name in selected_curves:
        df = property_data["curves"][curve_name]
        # Check if dataframe has at least 2 columns
        if len(df.columns) >= 2:
            x_col, y_col = df.columns[0], df.columns[1]
            
            # Use markers only if there's just one data point
            mode = 'lines+markers' if len(df) > 1 else 'markers'
            
            fig.add_trace(go.Scatter(
                x=df[x_col],
                y=df[y_col],
                mode=mode,
                name=curve_name
            ))
        else:
            st.warning(f"Curve '{curve_name}' contains insufficient data to plot.")

    fig.update_layout(
        title=f"{selected_property} vs. {x_label.split(',')[0]}",
        xaxis_title=x_label,
        yaxis_title=y_label,
        legend_title="Curves",
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 2. Prepare data for CSV export
    st.subheader("Data Export")
    st.markdown("Download the data for the currently selected curves as a CSV file.")
    
    csv_data = prepare_csv_export(property_data["curves"], selected_curves)
    
    if csv_data:
        # Sanitize filenames for download
        safe_material_name = "".join(c for c in selected_material if c.isalnum())
        safe_property_name = "".join(c for c in selected_property if c.isalnum())
        
        st.download_button(
           label="📥 Download Data as CSV",
           data=csv_data,
           file_name=f"{safe_material_name}_{safe_property_name}_data.csv",
           mime="text/csv",
        )