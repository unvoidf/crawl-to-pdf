# Website PDF Crawler

Python CLI tool that crawls all pages of a website and converts them to PDF format using Headless Chrome.

## Features

- **Automatic Crawling**: Automatically discovers all pages within a domain starting from a given URL
- **Domain Restriction**: Only crawls pages within the same domain
- **PDF Conversion**: Converts each page to PDF format
- **Smart Naming**: Automatically generates file names from page title and URL
- **Smart Append**: Doesn't create duplicate PDFs if content hasn't changed (hash-based verification)
- **Parallel Processing**: Crawls pages in parallel using multiple workers
- **Progress Tracking**: Shows processing progress
- **Detailed Reporting**: Created/Updated/Skipped statistics
- **Error Handling**: Logs errors and continues processing

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:

```bash
playwright install chromium
```

## Usage

### Basic Usage

```bash
python crawl_to_pdf.py www.example.com
```

### Examples

```bash
# With HTTPS
python crawl_to_pdf.py https://example.com

# With custom output folder
python crawl_to_pdf.py www.example.com --output my-pdfs

# Short form
python crawl_to_pdf.py example.com -o pdfs

# Automatic behavior for existing result folder
python crawl_to_pdf.py example.com --if-exists overwrite

# Parallel processing (4 workers)
python crawl_to_pdf.py example.com --workers 4

# Debug mode
python crawl_to_pdf.py example.com --debug
```

`--if-exists` options:

- `ask` (default): Prompts you to choose if folder already exists.
- `overwrite`: Deletes existing folder and starts fresh.
- `append`: **Smart Append** - Keeps existing PDFs. Creates new version only if content has changed (hash-based verification).
- `skip`: Skips pages that already have a PDF file.
- `update`: Regenerates PDFs only if website content has changed.
- `abort`: Stops without starting if folder exists.

### Smart Append Feature

**Append** mode now works intelligently:
- Content hash (SHA256) is calculated for each PDF and stored in `.hashes/` folder
- If content hasn't changed in new crawl, duplicate PDF is not created
- New numbered PDF is added only when content changes (e.g., `file_1.pdf`, `file_2.pdf`)
- **Update** and **Skip** modes also use the same hash verification

## Output

- PDFs are saved to `results/{domain}-pdfs` folder by default
- Example: `www.example.com` → `results/www-example-com-pdfs/` folder
- PDF names: `{Title}_{URL_segment}.pdf` format
- Each PDF header contains page URL and access time in `Access Date: YYYY-MM-DD HH:MM:SS TZ` format
- Example: `About_us_about.pdf`
- **Hash files**: Content hash for each PDF is stored in `.hashes/` subfolder (for Smart Append)
- **Summary report**: Detailed statistics are shown at the end of processing:
  ```
  Summary:
    Processed: X pages
    - Created: Y
    - Updated: Z
    - Skipped: W
    Errors: E
  ```

## How It Works

1. Starts from given URL
2. Extracts domain and creates folder
3. Launches Headless Chrome
4. Crawls pages using BFS (Breadth-First Search) algorithm:
   - Loads each page (DOMContentLoaded)
   - Extracts links from page
   - Adds new links from same domain to queue
   - Converts page to PDF
5. Shows summary when all pages are processed

## Technical Details

### URL Normalization
- Missing protocol is automatically added (https)
- Fragment (#) is removed
- Query parameters are preserved
- Trailing slash is normalized

### Domain Control
- Only links from the same domain are followed
- Subdomains are not included (www.example.com ≠ api.example.com)

### PDF Naming
- Generated from page title and last segment of URL
- Special characters are cleaned
- Turkish characters are converted to ASCII
- Sequential numbers are added for duplicate names

### Error Handling
- If page cannot be loaded: logged, skipped, continues
- If PDF cannot be created: logged, skipped, continues
- All errors are written to console and summary

## Requirements

- Python 3.7+
- Playwright
- Unidecode

## File Structure

```
BBB/
├── crawl_to_pdf.py          # Main CLI script
├── crawler_components/
│   ├── __init__.py          # Helper package definition
│   ├── url_manager.py       # URL management and domain control
│   ├── web_crawler.py       # Web crawling logic
│   ├── pdf_generator.py     # PDF generation
│   ├── file_name_generator.py # PDF naming
│   └── progress_tracker.py  # Progress tracking
├── results/                 # PDF outputs (gitignore)
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## Notes

- Playwright browsers will be downloaded on first run (a few hundred MB)
- Processing may take a long time for large websites
- No rate limiting, use carefully
- Some pages may load dynamic content with JavaScript, content may be incomplete in such cases

## License

This project is for educational purposes.
