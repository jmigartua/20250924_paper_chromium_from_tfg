# app_01_data_import.py (excerpt around provenance) -- this is a helper note:
# The enhanced app published earlier already includes a "Provenance & Version" section.
# To display a semantic version from a VERSION file, ensure this helper is present in the app:
def _app_version() -> str:
    try:
        with open("VERSION", "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "unversioned"

# Then in gather_provenance(), add "app_version": _app_version()
# And optionally show it in the UI near the title or in the Provenance JSON.
