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
# (Paste the exact same helper functions: sanitize_filename, find_doi,
#  get_bibtex_from_doi, find_oa_pdf_url, download_pdf from the previous
#  correct version here)
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
    ui.tags.style(""" .status-area { height: 250px; overflow-y: scroll; border: 1px solid #ccc; padding: 5px; margin-top: 10px; font-family: monospace; font-size: 0.9em; background-color: #f8f8f8; white-space: pre-wrap; } .row-inputs-log { margin-bottom: 20px; } """),
    ui.h2("Researcher Reference Tool"),
    ui.row( {"class": "row-inputs-log"},
        ui.column(5, ui.input_file("file_input", "Upload references.txt", accept=[".txt"], multiple=False), ui.input_selectize( "email_input", "Your Email (select or type new):", choices=INITIAL_EMAIL_LIST, selected=INITIAL_EMAIL_LIST[-1] if INITIAL_EMAIL_LIST else None, multiple=False, options={"create": True} ), ui.input_checkbox("download_pdf_check", "Attempt to download Open Access PDFs", value=False), ui.input_action_button( "process_button", ui.TagList(ui.tags.i(class_="fas fa-cogs"), " Process References"), class_="btn-primary" ), ),
        ui.column(7, ui.h4("Status Log"), ui.p(ui.tags.small("Real-time progress shown via transient notifications. Full log appears below upon completion.")), ui.output_text_verbatim("status_log_output", placeholder=True).add_class("status-area"), )
    ),
    ui.row( ui.column(12, ui.hr(), ui.h4("Results"), ui.output_ui("download_buttons_ui"), ui.output_data_frame("results_table") ) )
)

# --- Shiny App Server Logic ---
def server(input, output, session):
    results_data = reactive.Value(pd.DataFrame()); status_messages = reactive.Value(["Waiting for input..."]); pdf_zip_bytes = reactive.Value(None); is_processing = reactive.Value(False); known_emails = reactive.Value(load_emails())

    @render.text
    def status_log_output(): return "\n".join(status_messages())

    @reactive.Effect
    @reactive.event(input.process_button)
    async def run_processing():
        nonlocal known_emails
        if is_processing(): ui.notification_show("Processing already in progress.", type="warning"); return
        is_processing.set(True); results_data.set(pd.DataFrame()); pdf_zip_bytes.set(None)
        status_messages.set(["Processing started... Full log will appear upon completion."])
        ui.notification_show("Processing started...", duration=3)

        file_infos = input.file_input()
        if not file_infos: status_messages.set(["Error: No file uploaded."]); is_processing.set(False); return
        file_info = file_infos[0]
        email = input.email_input().strip()
        if not email or "@" not in email: status_messages.set(["Error: Please provide/select a valid email address."]); ui.notification_show("Valid email required.", type="error"); is_processing.set(False); return
        should_download = input.download_pdf_check()

        # --- Define the background processing function ---
        # --- Added main_loop parameter ---
        def background_processing_task(file_info, email, should_download, session: shiny.Session, main_loop):
            current_status = ["Background processing started..."]; results_list = []; temp_dir = None
            downloaded_files_info = []; processing_error = None

            try:
                file_path = file_info['datapath']
                with open(file_path, 'rb') as f: references_bytes = f.read()
                references_text = references_bytes.decode('utf-8')
                references = [line.strip() for line in references_text.splitlines() if line.strip()]
                if not references: raise ValueError("No valid references found in file.")
                current_status.append(f"Read {len(references)} references from '{file_info['name']}'.")

                if should_download: temp_dir = tempfile.mkdtemp(prefix="ref_tool_pdfs_"); current_status.append(f"Created temp dir: {temp_dir}")
                req_session = requests.Session(); req_session.headers.update({'User-Agent': f'ShinyResearcherTool/1.0 (mailto:{email})'})
                total_refs = len(references)

                for i, ref in enumerate(references):
                    progress_msg = f"Processing ref {i+1}/{total_refs}: {ref[:40]}..."
                    current_status.append(progress_msg)

                    # --- Use passed main_loop for scheduling notification ---
                    if main_loop and main_loop.is_running():
                        async def show_progress_notification(msg): ui.notification_show(msg, duration=2, type="message")
                        asyncio.run_coroutine_threadsafe(show_progress_notification(progress_msg), main_loop)
                    else:
                         print(f"Warning: Could not get running loop to show notification for ref {i+1}", file=sys.stderr)


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
        # --- End of background_processing_task definition ---

        # Run background task
        try:
            # --- Get main loop before starting thread ---
            main_event_loop = asyncio.get_running_loop()

            # --- Pass main_event_loop to the background task ---
            results_list, final_status, zip_data, error = await asyncio.to_thread(
                background_processing_task, file_info, email, should_download, session, main_event_loop
            )

            # Update UI after thread finishes
            status_messages.set(final_status)
            if error: ui.notification_show(f"Processing failed: Check Status Log. {error[:100]}...", type="error", duration=None)
            else:
                final_df = pd.DataFrame(results_list); results_data.set(final_df)
                if zip_data: pdf_zip_bytes.set(zip_data)
                ui.notification_show("Processing finished! Full log available.", duration=5, type="success")
                current_emails = known_emails() # Update email list
                if email not in current_emails:
                    new_email_list = sorted(list(set(current_emails + [email]))); save_emails(new_email_list)
                    known_emails.set(new_email_list); ui.update_selectize("email_input", choices=new_email_list, selected=email)
                else: ui.update_selectize("email_input", selected=email)
        except Exception as e:
            err_msg = f"Error initiating processing: {e}"; status_messages.set(["Processing started...", err_msg])
            print(err_msg, file=sys.stderr); traceback.print_exc(file=sys.stderr); ui.notification_show(err_msg, type="error", duration=None)
        finally: is_processing.set(False)

    # Other render functions
    @render.data_frame
    def results_table(): df = results_data(); req(df is not None and not df.empty); return render.DataGrid(df, width="100%", height="500px", selection_mode="none")
    @render.ui
    def download_buttons_ui():
        df = results_data(); zip_data = pdf_zip_bytes()
        if is_processing() or df is None or df.empty: return None
        csv_download = ui.download_button("download_csv", "Download Results (CSV)", class_="btn-success me-2")
        zip_download = None;
        if zip_data: zip_download = ui.download_button("download_zip", "Download PDFs (ZIP)", class_="btn-info")
        return ui.div(csv_download, zip_download)
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