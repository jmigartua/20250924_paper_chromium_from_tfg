.PHONY: run run-dev validate-templates clean

run:
	streamlit run app_01_data_import.py

run-dev:
	STREAMLIT_SERVER_HEADLESS=true streamlit run app_01_data_import.py

validate-templates:
	python schema_validator.py templates/sample_two_column.csv --base-x "T (K)" --property "Normal Total Emittance"
	python schema_validator.py templates/sample_grouped_long.csv --base-x "λ (µm)" --property "Normal Spectral Reflectance"
	python schema_validator.py templates/sample_wide_with_errors.csv --base-x "λ (µm)" --property "Normal Spectral Reflectance"

clean:
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
