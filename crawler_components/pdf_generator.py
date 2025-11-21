"""This file converts pages to PDF output using Playwright."""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
from playwright.async_api import Page
from .file_name_generator import FileNameGenerator


class PDFGenerator:
    """Generates PDF files from web pages."""
    
    def __init__(self, file_name_generator: FileNameGenerator):
        """Initialize PDF generator.
        
        Args:
            file_name_generator: File name generator instance
        """
        self.file_name_generator = file_name_generator
        
    def _create_header_template(self, url: str, accessed_display: str) -> str:
        """Create header template with URL information.
        
        Args:
            url: Page URL to display in header
            accessed_display: Human readable timestamp string
            
        Returns:
            HTML template string for PDF header
        """
        # Escape HTML characters in URL
        escaped_url = (
            url.replace('&', '&amp;')
               .replace('<', '&lt;')
               .replace('>', '&gt;')
               .replace('"', '&quot;')
               .replace("'", '&#x27;')
        )
        
        # Playwright header template format
        # Header template must be valid HTML with inline styles
        # Width should be specified, and content should fit within header area
        template = (
            '<div style="'
            'font-size: 9px; '
            'color: #444444; '
            'padding: 5px 15px; '
            'width: 100%; '
            'text-align: left; '
            'font-family: Arial, sans-serif; '
            'box-sizing: border-box; '
            'overflow: hidden; '
            'white-space: nowrap; '
            'text-overflow: ellipsis;'
            '">'
            f'<div style="margin-bottom:2px;"><span>{escaped_url}</span></div>'
            f'<div><span>Access Date: {accessed_display} by Crawl to PDF</span></div>'
            '</div>'
        )
        return template
    
    async def generate_pdf(
        self,
        page: Page,
        title: str,
        url: str,
        accessed_at: Optional[datetime] = None,
        exists_mode: str = 'append'
    ) -> Tuple[Optional[Path], str, Optional[str]]:
        """Generate PDF from current page.
        
        Args:
            page: Playwright page object
            title: Page title
            url: Page URL
            accessed_at: Datetime when the page was captured
            exists_mode: Behavior when file exists ('append', 'skip', 'update')
            
        Returns:
            Tuple of (PDF path or None, status, error message or None)
            Status: 'created', 'updated', 'skipped', 'unchanged', 'failed'
        """
        try:
            timestamp = accessed_at or datetime.now(timezone.utc).astimezone()
            accessed_display = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z%z")
            
            # Calculate content hash early for all modes
            import hashlib
            content = await page.content()
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Initialize pdf_path as None
            pdf_path = None
            
            # Handle 'skip' mode
            if exists_mode == 'skip':
                file_name = self.file_name_generator.get_base_name(title, url)
                pdf_path = self.file_name_generator.get_full_path(file_name)
                if pdf_path.exists():
                    return None, 'skipped', "Skipped (already exists)"
            
            # Handle 'update' mode
            elif exists_mode == 'update':
                file_name = self.file_name_generator.get_base_name(title, url)
                pdf_path = self.file_name_generator.get_full_path(file_name)
                if pdf_path.exists():
                    hash_path = self.file_name_generator.get_hash_path(pdf_path)
                    if hash_path.exists():
                        try:
                            old_hash = hash_path.read_text().strip()
                            if old_hash == content_hash:
                                return None, 'unchanged', "Skipped (content unchanged)"
                        except Exception:
                            # If hash file is corrupt or unreadable, proceed with update
                            pass
            
            # Handle 'append' mode (Smart Append)
            elif exists_mode == 'append':
                latest_version = self.file_name_generator.get_latest_version(title, url)
                if latest_version:
                    latest_hash_path = self.file_name_generator.get_hash_path(latest_version)
                    if latest_hash_path.exists():
                        try:
                            latest_hash = latest_hash_path.read_text().strip()
                            if latest_hash == content_hash:
                                return None, 'unchanged', "Skipped (content unchanged from latest version)"
                        except Exception:
                            pass
                
                # If we are here, it means content is new or no previous version exists
                # Generate a new unique name (standard append behavior)
                file_name = self.file_name_generator.generate_name(title, url)
                pdf_path = self.file_name_generator.get_full_path(file_name)
            
            # If pdf_path is still None (e.g., update mode but file doesn't exist yet, or overwrite/fresh mode),
            # set it using the appropriate method based on mode
            if not pdf_path:
                if exists_mode in ('skip', 'update', 'overwrite', 'fresh'):
                    file_name = self.file_name_generator.get_base_name(title, url)
                    pdf_path = self.file_name_generator.get_full_path(file_name)
                else:
                    # Default fallback (should not reach here normally)
                    return None, 'failed', f"Internal Error: PDF path not set for mode '{exists_mode}'"

            hash_path = self.file_name_generator.get_hash_path(pdf_path)
            
            header_template = self._create_header_template(url, accessed_display)
            
            await page.pdf(
                path=str(pdf_path),
                format='A4',
                print_background=True,
                display_header_footer=True,
                header_template=header_template,
                margin={
                    'top': '3cm',
                    'right': '1cm',
                    'bottom': '1cm',
                    'left': '1cm'
                }
            )
            
            # Write new hash
            try:
                # Ensure the directory for the hash file exists
                hash_path.parent.mkdir(parents=True, exist_ok=True)
                hash_path.write_text(content_hash)
            except Exception as e:
                print(f"Warning: Failed to write hash file: {e}", file=sys.stderr)
            
            status = 'updated' if (exists_mode == 'update' and pdf_path.exists()) else 'created'
            
            return pdf_path, status, None
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise cancellation to be handled by caller
            raise
        
        except Exception as e:
            return None, 'failed', str(e)

