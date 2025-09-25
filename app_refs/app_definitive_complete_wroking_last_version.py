# app.py
import shiny
from shiny import App, reactive, render, ui, req
from shiny.types import FileInfo
import pandas as pd
import requests
import json
import time
import os
import sys
import re
import zipfile
import tempfile
import shutil
import io
import traceback
from datetime import datetime
import asyncio # Ensure asyncio is imported

# --- Configuration & Constants ---
CROSSREF_API_URL = "https://api.crossref.org/works"
UNPAYWALL_API_URL = "https://api.unpaywall.org/v2/{doi}"
REQUEST_DELAY_SECONDS = 1
EMAIL_STORAGE_FILE = "user_emails.json"

# --- Helper Functions ---
# (PASTE THE EXACT SAME HELPER FUNCTIONS FROM THE PREVIOUS VERSION HERE)
# --- START HELPER FUNCTIONS ---
def sanitize_filename(filename):
    """Removes characters invalid for filenames."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename); sanitized = sanitized.replace(" ", "_")
    max_len = 200; return sanitized[:max_len] if len(sanitized) > max_len else sanitized
def find_doi(reference, email, session):
    if not isinstance(reference, str) or not reference.strip(): return None, "Empty Reference String"
    if not email: return None, "Email address required for API calls"
    params = {'query.bibliographic': reference, 'rows': 1, 'mailto': email}
    try:
        response = session.get(CROSSREF_API_URL, params=params, timeout=20); response.raise_for_status(); data = response.json()
        if data['message']['items']: doi = data['message']['items'][0].get('DOI'); return doi, "DOI Found"
        else: return None, "DOI Not Found (Crossref)"
    except requests.exceptions.Timeout: print(f"DEBUG: find_doi Timeout for '{reference[:50]}...'", file=sys.stderr); return None, "Crossref Timeout"
    except requests.exceptions.RequestException as e: print(f"DEBUG: find_doi Request Error for '{reference[:50]}...': {e}", file=sys.stderr); return None, f"Crossref Request Error ({e})"
    except json.JSONDecodeError: print(f"DEBUG: find_doi JSON Error for '{reference[:50]}...'", file=sys.stderr); return None, "Crossref JSON Error"
    except Exception as e: print(f"Unexpected error in find_doi for '{reference[:50]}...': {e}\n{traceback.format_exc()}", file=sys.stderr); return None, f"Unexpected DOI Error ({type(e).__name__})"
def get_bibtex_from_doi(doi, email, session):
    if not doi: return None, "No DOI provided"
    if not email: return None, "Email address required for API calls"
    try:
        url = f"https://doi.org/{doi}"; headers = {'Accept': 'application/x-bibtex; charset=utf-8', 'User-Agent': f'ShinyResearcherTool/1.0 (mailto:{email})'}
        response = session.get(url, headers=headers, timeout=15, allow_redirects=True); response.raise_for_status(); content_type = response.headers.get('Content-Type', '').lower()
        if 'application/x-bibtex' in content_type:
            bibtex_string = response.content.decode('utf-8', errors='replace')
            if bibtex_string.strip().startswith('@'): return bibtex_string, "BibTeX Found"
            else: print(f"DEBUG: get_bibtex Invalid content for {doi}: {bibtex_string[:100]}...", file=sys.stderr); return None, "Response not valid BibTeX"
        else: print(f"DEBUG: get_bibtex Wrong Content-Type for {doi}: {content_type}", file=sys.stderr); return None, f"BibTeX Not Returned (Type: {content_type})"
    except requests.exceptions.Timeout: print(f"DEBUG: get_bibtex Timeout for {doi}", file=sys.stderr); return None, "BibTeX Timeout"
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: get_bibtex Request Error for {doi}: {e}", file=sys.stderr)
        if e.response is not None and e.response.status_code == 404: return None, "BibTeX Not Found (404)"
        return None, f"BibTeX Request Error ({e})"
    except Exception as e: print(f"Unexpected error in get_bibtex_from_doi for '{doi}': {e}\n{traceback.format_exc()}", file=sys.stderr); return None, f"Unexpected BibTeX Error ({type(e).__name__})"
def find_oa_pdf_url(doi, email, session):
    if not doi: return None, "No DOI provided"
    if not email: return None, "Email address required for API calls"
    url = UNPAYWALL_API_URL.format(doi=doi); params = {'email': email}
    try:
        response = session.get(url, params=params, timeout=20)
        if response.status_code == 404: return None, "OA Status: Not Found (Unpaywall 404)"
        response.raise_for_status(); data = response.json()
        oa_location = data.get('best_oa_location')
        if oa_location and oa_location.get('url_for_pdf'): return oa_location['url_for_pdf'], "OA PDF Found (Unpaywall)"
        elif data.get('is_oa'):
             oa_url = oa_location.get('url') if oa_location else None
             if oa_url: return None, f"OA (No direct PDF link, try landing page)"
             else: return None, "OA (No PDF link found)"
        else: return None, "OA Status: Not Open Access"
    except requests.exceptions.Timeout: print(f"DEBUG: find_oa_pdf_url Timeout for {doi}", file=sys.stderr); return None, "Unpaywall Timeout"
    except requests.exceptions.RequestException as e: print(f"DEBUG: find_oa_pdf_url Request Error for {doi}: {e}", file=sys.stderr); return None, f"Unpaywall Request Error ({e})"
    except json.JSONDecodeError: print(f"DEBUG: find_oa_pdf_url JSON Error for {doi}", file=sys.stderr); return None, "Unpaywall JSON Error"
    except Exception as e: print(f"Unexpected error in find_oa_pdf_url for '{doi}': {e}\n{traceback.format_exc()}", file=sys.stderr); return None, f"Unexpected OA Error ({type(e).__name__})"
def download_pdf(pdf_url, doi, download_dir, session):
    if not pdf_url or not doi or not download_dir: return None, "PDF Download Error: Missing inputs"
    safe_doi_filename = sanitize_filename(doi.replace('/', '_')) + ".pdf"; filepath = os.path.join(download_dir, safe_doi_filename)
    if os.path.exists(filepath): return filepath, "PDF Already Existed"
    try:
        pdf_response = session.get(pdf_url, timeout=60, allow_redirects=True, stream=True); pdf_response.raise_for_status(); content_type = pdf_response.headers.get('content-type', '').lower()
        status_prefix = ""
        if 'application/pdf' not in content_type:
            status_prefix = f"PDF Warning: Content-Type '{content_type}'. "
            if 'text/html' in content_type: print(f"DEBUG: download_pdf Received HTML instead of PDF for {doi}", file=sys.stderr); return None, "PDF Download Failed: Received HTML"
        with open(filepath, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192): f.write(chunk)
        return filepath, status_prefix + "PDF Downloaded"
    except requests.exceptions.Timeout: print(f"DEBUG: download_pdf Timeout for {doi}", file=sys.stderr); return None, "PDF Download Timeout"
    except requests.exceptions.RequestException as e: print(f"DEBUG: download_pdf Request Error for {doi}: {e}", file=sys.stderr); return None, f"PDF Download Error ({e})"
    except Exception as e: print(f"Unexpected error in download_pdf for '{pdf_url}': {e}\n{traceback.format_exc()}", file=sys.stderr); return None, f"Unexpected PDF Download Error ({type(e).__name__})"
# --- END HELPER FUNCTIONS ---


# --- Email Persistence Functions ---
# (load_emails and save_emails functions remain the same)
def load_emails():
    emails = set();
    if os.path.exists(EMAIL_STORAGE_FILE):
        try:
            with open(EMAIL_STORAGE_FILE, 'r') as f: data = json.load(f); emails = set(item for item in data if isinstance(item, str) and "@" in item)
        except (json.JSONDecodeError, IOError) as e: print(f"Warning: Could not load email file '{EMAIL_STORAGE_FILE}': {e}", file=sys.stderr)
    return sorted(list(emails))
def save_emails(emails):
    try:
        with open(EMAIL_STORAGE_FILE, 'w') as f: json.dump(sorted(list(set(emails))), f, indent=2)
    except IOError as e: print(f"Warning: Could not save email file '{EMAIL_STORAGE_FILE}': {e}", file=sys.stderr)

# --- Shiny App UI ---
INITIAL_EMAIL_LIST = load_emails()

app_ui = ui.page_fluid(
    # --- Updated CSS ---
    ui.tags.style("""
        .status-area { height: 250px; overflow-y: scroll; border: 1px solid #ccc; padding: 5px; margin-top: 10px; font-family: monospace; font-size: 0.9em; background-color: #f8f8f8; white-space: pre-wrap; }
        .row-inputs-log { margin-bottom: 20px; }
        .input-description { font-size: 0.85em; color: #6c757d; margin-top: -8px; margin-bottom: 8px; }
        hr.input-separator { margin-top: 15px; margin-bottom: 15px; }
        .result-card { border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px; background-color: #fff; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        .result-card h5 { margin-top: 0; margin-bottom: 10px; font-size: 1.1em; word-break: break-word; color: #333; }
        .result-card .info-section { margin-bottom: 10px; padding: 10px 12px; border-left: 3px solid transparent; border-radius: 3px; }
        .result-card .info-section strong { display: inline-block; min-width: 90px; color: #555; margin-right: 5px; }
        .result-card pre { white-space: pre-wrap; word-break: break-all; background-color: #f8f9fa; padding: 8px; border: 1px solid #eee; max-height: 200px; overflow-y: auto; font-size: 0.9em; margin-top: 5px; }
        .doi-section { background: linear-gradient(to right, #e7f0f7, #f8fafd); border-left-color: #a0c4e4; }
        .bibtex-section { background: linear-gradient(to right, #eaf7f0, #fafffc); border-left-color: #a7d7b8; }
        .pdf-section { background: linear-gradient(to right, #f5f5f5, #fdfdfd); border-left-color: #cccccc; }
    """),
    ui.h2("Researcher Reference Tool"),

    # Row 1: Inputs and Status Log (Layout unchanged, only CSS added above)
    ui.row(
        {"class": "row-inputs-log"},
        ui.column(5,
            ui.input_file("file_input", "Upload references.txt", accept=[".txt"], multiple=False),
            ui.p(ui.tags.small("Upload a plain text file (UTF-8) with one reference per line."), class_="input-description"),
            ui.hr(class_="input-separator"),
            ui.input_text_area("text_area_ref", "Or Paste Single Reference:", rows=4, placeholder="Paste one full reference string here...\n(Will be used only if no file is uploaded)"),
            ui.hr(class_="input-separator"),
            ui.input_selectize( "email_input", "Your Email:", choices=INITIAL_EMAIL_LIST, selected=INITIAL_EMAIL_LIST[-1] if INITIAL_EMAIL_LIST else None, multiple=False, options={"create": True, "placeholder": "Select or type new email..."}),
            ui.p(ui.tags.small("Required for polite API usage. Select known or type new."), class_="input-description"),
            ui.input_checkbox("download_pdf_check", "Attempt to download Open Access PDFs", value=False),
            ui.p(ui.tags.small("Uses Unpaywall to find legally available OA PDFs only."), class_="input-description"),
            ui.input_action_button( "process_button", ui.TagList(ui.tags.i(class_="fas fa-cogs"), " Process References"), class_="btn-primary" ),
        ),
        ui.column(7,
            ui.h4("Status Log"), ui.p(ui.tags.small("Real-time progress shown via transient notifications. Full log appears below upon completion.")), ui.output_text_verbatim("status_log_output", placeholder=True).add_class("status-area"),
        )
    ),

    # Row 2: Results (Using the new UI output function)
    ui.row(
        ui.column(12,
            ui.hr(), ui.h4("Results"), ui.output_ui("download_buttons_ui"), ui.output_ui("results_output_ui") # Changed here
        )
    )
)


# --- Shiny App Server Logic ---
# (Server function remains EXACTLY the same, except for the results rendering part)
def server(input, output, session):

    results_data = reactive.Value(pd.DataFrame()) # Store data in DataFrame
    status_messages = reactive.Value(["Waiting for input..."])
    pdf_zip_bytes = reactive.Value(None)
    is_processing = reactive.Value(False)
    known_emails = reactive.Value(load_emails())

    @render.text
    def status_log_output(): return "\n".join(status_messages())

    # --- run_processing function (NO CHANGES NEEDED HERE) ---
    @reactive.Effect
    @reactive.event(input.process_button)
    async def run_processing():
        # (Paste the exact run_processing function from the previous version here)
        # --- START run_processing ---
        nonlocal known_emails
        if is_processing(): ui.notification_show("Processing already in progress.", type="warning"); return
        is_processing.set(True); results_data.set(pd.DataFrame()); pdf_zip_bytes.set(None)
        status_messages.set(["Processing started... Full log will appear upon completion."])
        ui.notification_show("Processing started...", duration=3)
        file_infos = input.file_input(); pasted_ref = input.text_area_ref().strip(); file_info = None
        input_data_for_task = None; data_type_for_task = None
        if file_infos: file_info = file_infos[0]; input_data_for_task = file_info; data_type_for_task = "file"
        elif pasted_ref: input_data_for_task = [pasted_ref]; data_type_for_task = "pasted"
        else: status_messages.set(["Error: Please upload a file or paste a reference."]); is_processing.set(False); return
        email = input.email_input().strip()
        if not email or "@" not in email: status_messages.set(["Error: Please provide/select a valid email address."]); ui.notification_show("Valid email required.", type="error"); is_processing.set(False); return
        should_download = input.download_pdf_check()
        def background_processing_task(input_data, data_type, email, should_download, session: shiny.Session, main_loop):
            current_status = ["Background processing started..."]; results_list = []; temp_dir = None; downloaded_files_info = []; processing_error = None; references_local = []
            try:
                if data_type == "file": file_info_local = input_data; file_path = file_info_local['datapath'];
                elif data_type == "pasted": references_local = input_data; current_status.append(f"Processing 1 reference from text area.")
                else: raise ValueError("Invalid data_type for background task.")
                if data_type == "file": # Read file only if type is file
                    with open(file_path, 'rb') as f: references_bytes = f.read()
                    references_text = references_bytes.decode('utf-8')
                    references_local = [line.strip() for line in references_text.splitlines() if line.strip()]
                    current_status.append(f"Read {len(references_local)} references from '{file_info_local['name']}'.")
                if not references_local: raise ValueError("No valid references found in input.")
                if should_download: temp_dir = tempfile.mkdtemp(prefix="ref_tool_pdfs_"); current_status.append(f"Created temp dir: {temp_dir}")
                req_session = requests.Session(); req_session.headers.update({'User-Agent': f'ShinyResearcherTool/1.0 (mailto:{email})'})
                total_refs = len(references_local)
                for i, ref in enumerate(references_local):
                    progress_msg = f"Processing ref {i+1}/{total_refs}: {ref[:40]}..."
                    current_status.append(progress_msg)
                    if main_loop and main_loop.is_running():
                        async def show_progress_notification(msg): ui.notification_show(msg, duration=2, type="message")
                        asyncio.run_coroutine_threadsafe(show_progress_notification(progress_msg), main_loop)
                    else: print(f"Warning: Could not get running loop to show notification for ref {i+1}", file=sys.stderr)
                    result_row = { 'Reference': ref, 'DOI': '', 'DOI_URL': '', 'DOI_Status': '', 'BibTeX': '', 'BibTeX_Status': '', 'PDF_URL': '', 'PDF_Download_Status': 'Not Attempted' if should_download else 'Download Disabled' }
                    doi, doi_status = find_doi(ref, email, req_session); result_row['DOI_Status'] = doi_status
                    if doi:
                        result_row['DOI'] = doi; result_row['DOI_URL'] = f"https://doi.org/{doi}"
                        bibtex_str, bibtex_status = get_bibtex_from_doi(doi, email, req_session); result_row['BibTeX_Status'] = bibtex_status
                        if bibtex_str: result_row['BibTeX'] = bibtex_str
                        if should_download:
                            pdf_url, oa_status = find_oa_pdf_url(doi, email, req_session); result_row['PDF_URL'] = pdf_url if pdf_url else ''
                            if pdf_url:
                                pdf_filepath, dl_status = download_pdf(pdf_url, doi, temp_dir, req_session); result_row['PDF_Download_Status'] = dl_status
                                if pdf_filepath: downloaded_files_info.append({'path': pdf_filepath, 'doi': doi})
                            else: result_row['PDF_Download_Status'] = oa_status
                        else: result_row['PDF_Download_Status'] = 'Download Disabled'
                    else: result_row['BibTeX_Status'] = 'N/A (No DOI)'; result_row['PDF_Download_Status'] = 'N/A (No DOI)' if should_download else 'Download Disabled'
                    results_list.append(result_row)
                    time.sleep(REQUEST_DELAY_SECONDS)
                req_session.close(); current_status.append("API processing complete.")
                zip_data_bytes = None
                if should_download and downloaded_files_info:
                    current_status.append("Creating ZIP archive...")
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                         for finfo in downloaded_files_info:
                            if os.path.exists(finfo['path']): zipf.write(finfo['path'], arcname=os.path.basename(finfo['path']))
                            else: current_status.append(f"Warning: PDF not found for zipping: {finfo['path']}")
                    zip_buffer.seek(0); zip_data_bytes = zip_buffer.getvalue()
                    current_status.append(f"ZIP archive created ({len(downloaded_files_info)} files).")
                current_status.append("Background processing finished.")
            except Exception as e: processing_error = f"Error during background processing: {e}\n{traceback.format_exc()}"; current_status.append(processing_error); print(processing_error, file=sys.stderr)
            finally:
                if temp_dir and os.path.exists(temp_dir):
                    try: shutil.rmtree(temp_dir); current_status.append("Cleaned up temporary PDF directory.")
                    except Exception as e: err_msg = f"Warning: Could not remove temp directory {temp_dir}: {e}"; current_status.append(err_msg); print(err_msg, file=sys.stderr)
            return results_list, current_status, zip_data_bytes, processing_error
        try:
            main_event_loop = asyncio.get_running_loop()
            results_list, final_status, zip_data, error = await asyncio.to_thread( background_processing_task, input_data_for_task, data_type_for_task, email, should_download, session, main_event_loop )
            status_messages.set(final_status)
            if error: ui.notification_show(f"Processing failed: Check Status Log. {error[:100]}...", type="error", duration=None)
            else:
                final_df = pd.DataFrame(results_list); results_data.set(final_df)
                if zip_data: pdf_zip_bytes.set(zip_data)
                ui.notification_show("Processing finished! Full log available.", duration=5, type="success")
                current_emails = known_emails()
                if email not in current_emails:
                    new_email_list = sorted(list(set(current_emails + [email]))); save_emails(new_email_list)
                    known_emails.set(new_email_list); ui.update_selectize("email_input", choices=new_email_list, selected=email)
                else: ui.update_selectize("email_input", selected=email)
        except Exception as e:
            err_msg = f"Error initiating processing: {e}"; status_messages.set(["Processing started...", err_msg])
            print(err_msg, file=sys.stderr); traceback.print_exc(file=sys.stderr); ui.notification_show(err_msg, type="error", duration=None)
        finally: is_processing.set(False)
        # --- END run_processing ---


    # --- Updated results rendering function ---
    @render.ui
    def results_output_ui():
        df = results_data()
        req(df is not None and not df.empty) # Require data
        cards = []
        for index, row in df.iterrows():
            # DOI Section
            doi_section_content = [ui.tags.strong("Status:"), row['DOI_Status']]
            if pd.notna(row['DOI']) and row['DOI']: doi_section_content.extend([ ui.br(), ui.tags.strong("DOI:"), row['DOI'], ui.br(), ui.tags.strong("URL:"), ui.a(row['DOI_URL'], href=row['DOI_URL'], target="_blank") ])
            # BibTeX Section
            bibtex_section_content = [ui.tags.strong("Status:"), row['BibTeX_Status']]
            if pd.notna(row['BibTeX']) and row['BibTeX']: bibtex_section_content.extend([ui.br(), ui.tags.strong("Entry:"), ui.pre(row['BibTeX'])])
            # PDF Section
            pdf_section_content = [ui.tags.strong("Status:"), row['PDF_Download_Status']]
            if pd.notna(row['PDF_URL']) and row['PDF_URL']: pdf_section_content.extend([ui.br(), ui.tags.strong("OA URL:"), ui.a(row['PDF_URL'], href=row['PDF_URL'], target="_blank")])
            # Build Card
            card = ui.div( {"class": "result-card"}, ui.tags.h5(f"Reference {index + 1}:"), ui.p(row['Reference']), ui.hr(),
                ui.div({"class": "info-section doi-section"}, ui.h6("DOI Information"), ui.TagList(doi_section_content)),
                ui.div({"class": "info-section bibtex-section"}, ui.h6("BibTeX Information"), ui.TagList(bibtex_section_content)),
                ui.div({"class": "info-section pdf-section"}, ui.h6("PDF Information"), ui.TagList(pdf_section_content)),
            )
            cards.append(card)
        return ui.TagList(*cards)

    # --- Download Buttons UI (no change) ---
    @render.ui
    def download_buttons_ui():
        df = results_data(); zip_data = pdf_zip_bytes()
        if is_processing() or df is None or df.empty: return None
        csv_download = ui.download_button("download_csv", "Download Results (CSV)", class_="btn-success me-2")
        zip_download = None;
        if zip_data: zip_download = ui.download_button("download_zip", "Download PDFs (ZIP)", class_="btn-info")
        return ui.div(csv_download, zip_download)

    # --- Download Handlers (no change) ---
    @render.download(filename=lambda: f"reference_results_{datetime.now():%Y%m%d_%H%M%S}.csv")
    def download_csv(): 
        df = results_data(); 
        req(df is not None and not df.empty); 
        with io.StringIO() as buf: 
            df.to_csv(buf, index=False, encoding='utf-8'); 
            yield buf.getvalue()
    @render.download(filename=lambda: f"downloaded_pdfs_{datetime.now():%Y%m%d_%H%M%S}.zip")
    def download_zip(): 
        zip_data = pdf_zip_bytes(); 
        req(zip_data is not None); 
        yield zip_data

# --- App Definition ---
app = App(app_ui, server)