"""Bu dosya Playwright ile sayfaları PDF çıktısına dönüştürür."""
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
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Generate PDF from current page.
        
        Args:
            page: Playwright page object
            title: Page title
            url: Page URL
            accessed_at: Datetime when the page was captured
            
        Returns:
            Tuple of (PDF path or None, error message or None)
        """
        try:
            timestamp = accessed_at or datetime.now(timezone.utc).astimezone()
            accessed_display = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z%z")
            file_name = self.file_name_generator.generate_name(title, url)
            pdf_path = self.file_name_generator.get_full_path(file_name)
            
            header_template = self._create_header_template(url, accessed_display)
            
            await page.pdf(
                path=str(pdf_path),
                format='A4',
                print_background=True,
                display_header_footer=True,
                header_template=header_template,
                margin={
                    'top': '3cm',  # Increased top margin for header
                    'right': '1cm',
                    'bottom': '1cm',
                    'left': '1cm'
                }
            )
            
            return pdf_path, None
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise cancellation to be handled by caller
            raise
        
        except Exception as e:
            return None, str(e)

