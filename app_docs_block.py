# --- Documentation area: renders docs/ markdown files -------------------------
st.divider()
st.subheader("Documentation")

def _read_md(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"**Missing file:** `{path}`. Add the docs folder to the repository."
    except Exception as e:
        return f"**Error reading `{path}`:** {e}"

tab_usage, tab_conventions, tab_faq = st.tabs(
    ["Usage Guide", "Data Conventions", "FAQ"]
)

with tab_usage:
    st.markdown(_read_md("docs/usage.md"))

with tab_conventions:
    st.markdown(_read_md("docs/data-conventions.md"))

with tab_faq:
    st.markdown(_read_md("docs/faq.md"))
