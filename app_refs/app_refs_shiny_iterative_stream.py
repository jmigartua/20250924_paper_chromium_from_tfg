from __future__ import annotations

import asyncio
import io
import os
import re
import time
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd
import requests
from shiny import App, reactive, render, ui
import shinyswatch

# -----------------------------
# Configuration / etiquette
# -----------------------------
APP_NAME = "ResearcherRefTool"
APP_VER = "1.0"
DEFAULT_TIMEOUT = 20
CROSSREF_BASE = "https://api.crossref.org/works"
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
DOI_RESOLVER = "https://doi.org"

# Rate-limiting (very conservative; Crossref asks to be polite)
MIN_DELAY_SEC = 0.4  # ~2.5 req/s max; adjust if needed

# -----------------------------
# Simple DOI utilities
# -----------------------------
DOI_RE = re.compile(r"\\b10\\.\\d{4,9}/[-._;()/:A-Za-z0-9]+\\b", re.I)

def find_explicit_doi(text: str) -> Optional[str]:
    if not text:
        return None
    m = DOI_RE.search(text)
    if not m:
        return None
    doi = m.group(0).strip().strip(".").strip(";")
    # Normalize some common artifacts
    doi = doi.replace("http://dx.doi.org/", "").replace("https://dx.doi.org/", "")
    doi = doi.replace("http://doi.org/", "").replace("https://doi.org/", "")
    return doi

def polite_headers(email: str) -> Dict[str, str]:
    ua = f"{APP_NAME}/{APP_VER} (mailto:{email}) requests"
    return {"User-Agent": ua}

# -----------------------------
# Crossref search
# -----------------------------
def crossref_find_doi(ref: str, email: str, ses: requests.Session) -> Tuple[Optional[str], str]:
    """
    Returns (doi, status). Tries explicit DOI first; falls back to Crossref.
    """
    explicit = find_explicit_doi(ref)
    if explicit:
        return explicit, "doi-inline"

    try:
        params = {"query.bibliographic": ref, "rows": 3, "mailto": email}
        r = ses.get(CROSSREF_BASE, params=params, headers=polite_headers(email), timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            return None, f"crossref_http_{r.status_code}"
        data = r.json()
        items = data.get("message", {}).get("items", [])
        if not items:
            return None, "crossref_no_match"
        # Take the first item. More sophisticated scoring can be added.
        doi = items[0].get("DOI")
        if doi:
            return doi, "crossref_match"
        return None, "crossref_no_doi"
    except Exception as e:
        return None, f"crossref_error:{e.__class__.__name__}"

# -----------------------------
# BibTeX via doi.org content negotiation
# -----------------------------
def fetch_bibtex(doi: str, email: str, ses: requests.Session) -> Tuple[Optional[str], str]:
    """
    Uses content negotiation at doi.org to retrieve BibTeX.
    """
    try:
        url = f"{DOI_RESOLVER}/{doi}"
        headers = dict(polite_headers(email))
        headers["Accept"] = "application/x-bibtex"
        r = ses.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 200 and r.text and "@article" in r.text.lower():
            return r.text, "ok"
        elif r.status_code == 200:
            return r.text, "ok_nonarticle"
        else:
            return None, f"doi_http_{r.status_code}"
    except Exception as e:
        return None, f"doi_error:{e.__class__.__name__}"

# -----------------------------
# Unpaywall best_oa_location
# -----------------------------
def unpaywall_pdf_url(doi: str, email: str, ses: requests.Session) -> Tuple[Optional[str], str]:
    try:
        url = f"{UNPAYWALL_BASE}/{doi}"
        params = {"email": email}
        r = ses.get(url, params=params, headers=polite_headers(email), timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            return None, f"unpaywall_http_{r.status_code}"
        data = r.json()
        best = data.get("best_oa_location") or {}
        pdf = best.get("url_for_pdf")
        if pdf:
            return pdf, "ok"
        # fallback: scan oa_locations
        for loc in data.get("oa_locations") or []:
            if loc.get("url_for_pdf"):
                return loc["url_for_pdf"], "fallback"
        return None, "no_pdf"
    except Exception as e:
        return None, f"unpaywall_error:{e.__class__.__name__}"

# -----------------------------
# PDF download
# -----------------------------
def safe_name_from_doi(doi: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", doi)

def download_pdf(pdf_url: str, doi: str, out_dir: str, ses: requests.Session) -> Tuple[Optional[str], str]:
    try:
        os.makedirs(out_dir, exist_ok=True)
        fn = safe_name_from_doi(doi) + ".pdf"
        path = os.path.join(out_dir, fn)
        with ses.get(pdf_url, headers=polite_headers("pdf@local"), stream=True, timeout=DEFAULT_TIMEOUT) as r:
            if r.status_code != 200:
                return None, f"pdf_http_{r.status_code}"
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
        return path, "ok"
    except Exception as e:
        return None, f"pdf_error:{e.__class__.__name__}"

# -----------------------------
# Shiny UI
# -----------------------------
try:
    THEME = getattr(shinyswatch, "flatly")
except Exception:
    THEME = None

app_ui = ui.page_fluid(
    ui.layout_columns(
        ui.card(
            ui.h3("Researcher Reference Tool — REAL scraping"),
            ui.input_file("file_input", "Upload references.txt", multiple=False, accept=[".txt"]),
            ui.hr(),
            ui.input_text_area(
                "text_area_ref",
                "Or Paste Single Reference",
                placeholder="Paste one full reference string here… (used in addition to upload, if any)",
                height="120px",
            ),
            ui.hr(),
            ui.input_selectize(
                "email_input",
                "Your Email",
                choices=["jmigartua@mail.com"],
                selected="jmigartua@mail.com",
                options={"create": True, "persist": True},
            ),
            ui.input_checkbox("download_pdf_check", "Attempt to download Open Access PDFs", value=True),
            ui.row(
                ui.input_action_button("process_button", "Process References", class_="btn-primary"),
                ui.input_action_button("cancel_button", "Cancel", class_="ms-2"),
            ),
            ui.accordion(
                ui.accordion_panel(
                    "Debug: inputs",
                    ui.output_code("debug_inputs"),
                ),
                id="dbg", open=False,
            ),
            width=4,
        ),
        ui.card(
            ui.h3("Status Log"),
            ui.p("Before/after messages per reference. If anything fails you will see the HTTP/exception status."),
            ui.output_ui("progress_bar_ui"),
            ui.div(
                ui.output_ui("status_log_output"),
                style="max-height: 50vh; overflow:auto; border:1px solid #eee; padding:0.5rem; border-radius:6px;",
            ),
            width=8,
        ),
        col_widths=(4, 8),
    ),
    ui.hr(),
    ui.card(
        ui.h4("Results (updates live)"),
        ui.output_data_frame("results_df"),
        ui.row(
            ui.download_button("dl_results", "Download Results CSV"),
            ui.download_button("dl_log", "Download Status Log", class_="ms-2"),
        ),
    ),
    theme=THEME,
)

# -----------------------------
# Shiny server
# -----------------------------
def server(input, output, session):
    logs = reactive.Value([])
    results = reactive.Value(pd.DataFrame(columns=["#","Reference","DOI","DOI_Status","BibTeX_Status","PDF_Status","PDF_Path"]))
    progress = reactive.Value({"done": 0, "total": 0})
    cancel_flag = reactive.Value(False)

    def log(msg: str) -> None:
        logs.set([*logs.get(), msg])

    def append_row(row: Dict[str, Any]) -> None:
        df = results.get()
        results.set(pd.concat([df, pd.DataFrame([row])], ignore_index=True))

    def set_prog(done: int, total: int) -> None:
        progress.set({"done": int(done), "total": int(total)})

    def read_refs_now() -> Tuple[List[str], Dict[str, Any]]:
        meta: Dict[str, Any] = {"datapath": None, "exists": None, "size": None}
        refs: List[str] = []
        files = input.file_input()
        if files:
            dp = files[0]["datapath"]
            meta["datapath"] = dp
            meta["exists"] = os.path.exists(dp)
            meta["size"] = os.path.getsize(dp) if meta["exists"] else None
            if meta["exists"]:
                with open(dp, "rb") as fh:
                    txt = fh.read().decode("utf-8", errors="ignore")
                refs.extend([ln.strip() for ln in txt.splitlines() if ln.strip() and not ln.strip().startswith("#")])
        pasted = (input.text_area_ref() or "").strip()
        if pasted:
            refs.append(pasted)
        return refs, meta

    # ------------- per-item real work -------------
    def process_one_reference(ref: str, email: str, download_pdfs: bool) -> Tuple[Dict[str, Any], List[str]]:
        """
        Blocking worker, called via asyncio.to_thread.
        Returns (row, step_log).
        """
        step_log: List[str] = []
        ses = requests.Session()
        ses.headers.update(polite_headers(email))
        try:
            # 1) DOI
            doi, doi_status = crossref_find_doi(ref, email, ses)
            step_log.append(f"DOI: {doi or '—'} ({doi_status})")
            if not doi:
                return {"Reference": ref, "DOI": "", "DOI_Status": doi_status, "BibTeX_Status": "skipped", "PDF_Status": "skipped", "PDF_Path": ""}, step_log
            # polite delay
            time.sleep(MIN_DELAY_SEC)

            # 2) BibTeX
            bibtex, bib_status = fetch_bibtex(doi, email, ses)
            step_log.append(f"BibTeX: {bib_status}")
            # polite delay
            time.sleep(MIN_DELAY_SEC)

            # 3) OA/PDF
            pdf_status = "disabled"
            pdf_path = ""
            if download_pdfs:
                pdf_url, oa_status = unpaywall_pdf_url(doi, email, ses)
                step_log.append(f"Unpaywall: {oa_status}{' (pdf found)' if pdf_url else ''}")
                if pdf_url:
                    # store in ./downloads
                    out_dir = os.path.join(os.getcwd(), "downloads")
                    path, dl_status = download_pdf(pdf_url, doi, out_dir, ses)
                    pdf_status = dl_status
                    pdf_path = path or ""
                else:
                    pdf_status = oa_status
                time.sleep(MIN_DELAY_SEC)

            row = {
                "Reference": ref,
                "DOI": doi,
                "DOI_Status": doi_status,
                "BibTeX_Status": bib_status,
                "PDF_Status": pdf_status,
                "PDF_Path": pdf_path,
            }
            return row, step_log
        finally:
            try:
                ses.close()
            except Exception:
                pass

    # ------------- start button -------------
    @reactive.effect
    @reactive.event(input.process_button)
    async def _start():
        refs, meta = read_refs_now()
        log(f"[debug] datapath={meta['datapath']} exists={meta['exists']} size={meta['size']}")
        if not refs:
            ui.notification_show("Please upload a .txt and/or paste a reference.", type="warning")
            return

        # reset
        logs.set([])
        results.set(pd.DataFrame(columns=["#","Reference","DOI","DOI_Status","BibTeX_Status","PDF_Status","PDF_Path"]))
        cancel_flag.set(False)
        set_prog(0, len(refs))
        ui.notification_show(f"Processing {len(refs)} reference(s)…", type="message")

        # iterate
        for i, ref in enumerate(refs, start=1):
            if cancel_flag.get():
                log("Processing cancelled by user.")
                break

            log(f"▶️  [{i}/{len(refs)}] Starting: {ref[:120]}…")
            set_prog(i-1, len(refs))
            try:
                row, step_log = await asyncio.to_thread(process_one_reference, ref, input.email_input(), bool(input.download_pdf_check()))
                for msg in step_log:
                    log("   • " + msg)
                append_row({"#": i, **row})
                log(f"✅ [{i}/{len(refs)}] Finished.")
            except Exception as e:
                append_row({"#": i, "Reference": ref, "DOI": "", "DOI_Status": f"error:{e.__class__.__name__}", "BibTeX_Status": "error", "PDF_Status": "skipped", "PDF_Path": ""})
                log(f"❌ [{i}/{len(refs)}] Error: {e}")
            set_prog(i, len(refs))
            await asyncio.sleep(0)  # repaint

        log("All done.")

    @reactive.effect
    @reactive.event(input.cancel_button)
    def _cancel():
        cancel_flag.set(True)
        ui.notification_show("Cancel requested.", type="warning")

    # ------------- outputs -------------
    @output
    @render.ui
    def status_log_output():
        return ui.pre("\\n".join(logs.get()) or "(no messages yet)")

    @output
    @render.ui
    def progress_bar_ui():
        st = progress.get()
        done, total = st.get("done", 0), st.get("total", 0)
        pct = int(round(100 * done / total)) if total else 0
        return ui.div(
            {"class": "progress", "style": "height: 18px; margin-bottom: 8px;"},
            ui.div(
                {"class": "progress-bar", "role": "progressbar", "style": f"width: {pct}%;",
                 "aria-valuenow": str(pct), "aria-valuemin": "0", "aria-valuemax": "100"},
                f"{pct}%",
            ),
        )

    @output
    @render.data_frame
    def results_df():
        df = results.get()
        return df if df is not None and not df.empty else pd.DataFrame(columns=["#","Reference","DOI","DOI_Status","BibTeX_Status","PDF_Status","PDF_Path"])

    @output
    @render.code
    def debug_inputs():
        files = input.file_input()
        meta = None
        if files:
            dp = files[0]["datapath"]
            meta = {
                "name": files[0]["name"],
                "datapath": dp,
                "exists": os.path.exists(dp),
                "size": os.path.getsize(dp) if os.path.exists(dp) else None,
            }
        import json
        return json.dumps({
            "file_input": meta,
            "text_area_ref": (input.text_area_ref() or "").strip(),
            "email_input": input.email_input(),
            "download_pdf_check": bool(input.download_pdf_check()),
        }, indent=2)

app = App(app_ui, server)