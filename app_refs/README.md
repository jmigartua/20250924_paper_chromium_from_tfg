# Researcher Reference Tool

A comprehensive Shiny web application designed to help researchers automatically process academic references, find DOIs, retrieve BibTeX citations, and download open access PDFs.

## Overview

The Researcher Reference Tool is built using Python Shiny and provides an intuitive web interface for batch processing academic references. It integrates with multiple APIs to provide comprehensive bibliographic services while respecting copyright and API usage policies.

## Features

### 🔍 **DOI Discovery**
- Automatic DOI lookup using Crossref API
- Handles various reference formats
- Detailed status reporting for each lookup attempt
- Intelligent parsing of bibliographic information

### 📚 **BibTeX Generation**
- Automatic retrieval of properly formatted BibTeX entries
- Uses DOI resolution for accurate citation data
- Handles encoding and formatting issues gracefully
- Ready-to-use citations for reference managers

### 📄 **Open Access PDF Download**
- Integration with Unpaywall API for legal PDF access
- Only downloads open access content (respects copyright)
- Organized ZIP archives of downloaded PDFs
- Automatic file naming and organization

### ⚡ **Batch Processing**
- Process multiple references from uploaded text files
- Single reference input via text area
- Real-time progress notifications
- Asynchronous processing for better performance

### 💾 **Data Export**
- CSV export with comprehensive results and metadata
- ZIP download of collected PDFs
- Timestamped file naming for organization
- Persistent email storage for convenience

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Internet connection for API access
- Valid email address (required for API compliance)

### Required Dependencies

```bash
pip install shiny pandas requests
```

### Running the Application

#### Standard Shiny Execution

**Basic command:**
```bash
shiny run app_definitive_complete_working_last_version_4packing.py
```

**Recommended development command (with auto-reload and browser launch):**
```bash
shiny run --reload --launch-browser app_definitive_complete_working_last_version_4packing.py
```

#### Common Shiny Run Options

| Option | Description | Example |
|--------|-------------|----------|
| `--reload` | Automatically restart the app when code changes are detected | `shiny run --reload app.py` |
| `--launch-browser` | Automatically open the app in your default web browser | `shiny run --launch-browser app.py` |
| `--host` | Specify the host address (default: 127.0.0.1) | `shiny run --host 0.0.0.0 app.py` |
| `--port` | Specify the port number (default: 8000) | `shiny run --port 3000 app.py` |
| `--dev-mode` | Enable development mode with enhanced debugging | `shiny run --dev-mode app.py` |
| `--log-level` | Set logging level (debug, info, warning, error) | `shiny run --log-level debug app.py` |
| `--app-dir` | Specify the application directory | `shiny run --app-dir /path/to/app app.py` |

#### Complete Development Command

```bash
shiny run --reload --launch-browser --dev-mode --log-level info app_definitive_complete_working_last_version_4packing.py
```

#### Production-Ready Command

```bash
shiny run --host 0.0.0.0 --port 8000 app_definitive_complete_working_last_version_4packing.py
```

#### Additional Options

- `--help`: Display all available options
- `--version`: Show Shiny version
- `--factory`: Use when your app is created by a factory function

The application will start a local Shiny server. Open your browser and navigate to the provided URL (typically `http://127.0.0.1:8000`).

#### PyInstaller Bundle

If packaged as an executable:
1. Double-click the application file
2. Browser will automatically open to `http://127.0.0.1:8000`
3. No additional setup required

## User Guide

### Step 1: Prepare Your References

#### Option A: Upload Text File

Create a plain text file (UTF-8 encoding) with one complete reference per line:



Smith, J. (2023). Machine Learning in Climate Science. Nature Climate Change, 13(4), 123-135.
Johnson, A., & Brown, B. (2022). Deep Learning Applications. Science, 376(6594), 456-467.
Wilson, C., Davis, D., & Miller, E. (2021). Artificial Intelligence in Research. Cell, 184(10), 2567-2580.


#### Option B: Single Reference Input

Use the text area for processing individual references. Paste the complete citation string. This option is used only if no file is uploaded.

### Step 2: Configure Settings

#### Email Address (Required)
- Select from previously used emails or enter a new one
- Required for polite API usage (Crossref/Unpaywall policies)
- Email addresses are stored locally for future convenience
- Use institutional or professional email addresses when possible

#### PDF Download Option
- Check "Attempt to download Open Access PDFs" if desired
- Only downloads legally available open access content
- Creates ZIP archive of successful downloads
- Respects publisher copyright restrictions

### Step 3: Process References

1. Click the "Process References" button
2. Monitor progress through:
   - **Real-time notifications**: Brief progress updates
   - **Status log area**: Detailed processing information
3. Processing includes:
   - DOI lookup for each reference
   - BibTeX retrieval for found DOIs
   - PDF discovery and download (if enabled)
   - Comprehensive error handling and reporting

### Step 4: Review Results

Each processed reference displays three information sections:

#### DOI Information
- **Status**: Success/failure of DOI lookup
- **DOI**: Digital Object Identifier if found
- **URL**: Clickable link to official DOI page

#### BibTeX Information
- **Status**: Success/failure of BibTeX retrieval
- **Entry**: Complete BibTeX citation (if available)
- **Formatting**: Ready for use in LaTeX documents

#### PDF Information
- **Status**: Open access availability and download status
- **OA URL**: Direct link to open access PDF (if available)
- **Download**: Local file availability

### Step 5: Export Data

#### CSV Export
- Downloads comprehensive results table
- Includes all status information and metadata
- Filename format: `reference_results_YYYYMMDD_HHMMSS.csv`
- Compatible with Excel and other spreadsheet applications

#### PDF ZIP Export
- Available only if PDFs were successfully downloaded
- Contains all retrieved open access PDFs
- Filename format: `downloaded_pdfs_YYYYMMDD_HHMMSS.zip`
- Individual PDFs named by sanitized DOI

## Technical Details

### API Integration

- **Crossref API**: DOI discovery and metadata retrieval
- **Unpaywall API**: Open access status and PDF URLs
- **DOI Resolution**: BibTeX format retrieval
- **Rate Limiting**: 1-second delay between requests for API compliance

### File Handling

- **Input**: UTF-8 encoded text files
- **Output**: CSV (UTF-8), ZIP archives
- **Temporary Files**: Automatically cleaned after processing
- **Persistence**: Email storage in `user_emails.json`

### Error Handling

- Comprehensive error reporting for each processing step
- Timeout handling for network requests (20s for API calls, 60s for downloads)
- Graceful degradation when services are unavailable
- Detailed status messages for troubleshooting

## Best Practices

### Reference Quality

✅ **Do:**
- Use complete, well-formatted citations
- Include journal names, volumes, page numbers
- Provide author names in standard format
- Include publication years

❌ **Avoid:**
- Abbreviated or incomplete references
- References without sufficient bibliographic information
- Non-standard citation formats

### Batch Processing

- Process reasonable batch sizes (recommended: < 100 references)
- Allow sufficient time for API rate limiting
- Monitor status log for any processing issues
- Consider breaking large batches into smaller chunks

### Email Usage

- Use institutional or professional email addresses
- Required for API compliance and potential rate limit increases
- Stored locally for convenience in future sessions
- Helps maintain good standing with API providers

### PDF Downloads

- Only downloads legally available open access content
- Respects publisher copyright restrictions
- Check PDF quality and completeness after download
- Not all papers will have open access versions available

## Troubleshooting

### Common Issues

#### "Email address required" Error
**Solution:**
- Ensure a valid email is entered or selected
- Email must contain "@" symbol
- Try selecting from dropdown or typing new email

#### "No valid references found" Error
**Solutions:**
- Check file encoding (must be UTF-8)
- Ensure one reference per line in text file
- Verify references are complete citations
- Try processing a single reference first

#### API Timeouts or Errors
**Solutions:**
- Check internet connection
- Wait and retry (APIs may be temporarily unavailable)
- Reduce batch size if processing large numbers
- Check status log for specific error details

#### PDF Download Failures
**Expected Behavior:**
- Many papers are not open access
- Publisher restrictions may apply
- Check "OA URL" links manually if needed
- Not all DOIs will have downloadable PDFs

### Performance Tips

- Process references during off-peak hours for better API response
- Use wired internet connection for stability
- Close unnecessary browser tabs to free memory
- Monitor system resources during large batch processing

## Output File Structure

### CSV Columns

| Column | Description |
|--------|-------------|
| `Reference` | Original reference text |
| `DOI` | Found DOI (if any) |
| `DOI_URL` | DOI resolution URL |
| `DOI_Status` | Success/failure status for DOI lookup |
| `BibTeX` | Complete BibTeX entry |
| `BibTeX_Status` | Retrieval status for BibTeX |
| `PDF_URL` | Open access PDF URL |
| `PDF_Download_Status` | Download attempt status |

### ZIP Contents

- Individual PDF files named by sanitized DOI
- Format: `{doi_with_underscores}.pdf`
- Example: `10.1038_s41586-021-03819-2.pdf`

## API Compliance

This tool follows best practices for academic API usage:

- **Rate Limiting**: Implements delays between requests
- **User Identification**: Requires email for API calls
- **Respectful Usage**: Only accesses open access content
- **Error Handling**: Graceful handling of API limitations

## License & Usage

This tool is designed for academic and research purposes. Users are responsible for:

- Complying with institutional policies
- Respecting copyright and publisher terms
- Using downloaded content appropriately
- Following API terms of service

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the status log for detailed error information
3. Ensure all prerequisites are met
4. Verify internet connectivity and API availability

## Version Information

- **Application**: Researcher Reference Tool
- **File**: `app_definitive_complete_working_last_version_4packing.py`
- **Framework**: Python Shiny
- **APIs**: Crossref, Unpaywall, DOI Resolution

---

*This tool streamlines the research workflow by automating tedious reference processing tasks while maintaining compliance with academic publishing standards and copyright restrictions.*