"""PDF generation from web pages using Playwright."""
import asyncio
from pathlib import Path
from playwright.async_api import Page
from typing import Optional
from file_name_generator import FileNameGenerator


class PDFGenerator:
    """Generates PDF files from web pages."""
    
    def __init__(self, file_name_generator: FileNameGenerator):
        """Initialize PDF generator.
        
        Args:
            file_name_generator: File name generator instance
        """
        self.file_name_generator = file_name_generator
        
    def _create_header_template(self, url: str) -> str:
        """Create header template with URL information.
        
        Args:
            url: Page URL to display in header
            
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
            'color: #666666; '
            'padding: 5px 15px; '
            'width: 100%; '
            'text-align: left; '
            'font-family: Arial, sans-serif; '
            'box-sizing: border-box; '
            'overflow: hidden; '
            'white-space: nowrap; '
            'text-overflow: ellipsis;'
            '">'
            f'<span style="display: inline-block;">{escaped_url}</span>'
            '</div>'
        )
        return template
    
    async def generate_pdf(self, page: Page, title: str, url: str) -> Optional[Path]:
        """Generate PDF from current page.
        
        Args:
            page: Playwright page object
            title: Page title
            url: Page URL
            
        Returns:
            Path to generated PDF file, or None if generation failed
        """
        try:
            file_name = self.file_name_generator.generate_name(title, url)
            pdf_path = self.file_name_generator.get_full_path(file_name)
            
            header_template = self._create_header_template(url)
            
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
            
            return pdf_path
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise cancellation to be handled by caller
            raise
        
        except Exception as e:
            # Error will be logged by caller
            return None

