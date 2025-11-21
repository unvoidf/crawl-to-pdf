"""Web crawling logic using Playwright."""
import asyncio
from playwright.async_api import Browser, Page, TimeoutError as PlaywrightTimeoutError
from typing import List, Optional
from url_manager import URLManager


class WebCrawler:
    """Handles web page loading and link extraction."""
    
    def __init__(self, browser: Browser, url_manager: URLManager):
        """Initialize web crawler.
        
        Args:
            browser: Playwright browser instance
            url_manager: URL manager instance
        """
        self.browser = browser
        self.url_manager = url_manager
        
    async def load_page(self, url: str, timeout: int = 30000) -> Optional[Page]:
        """Load a web page and wait for DOMContentLoaded.
        
        Args:
            url: URL to load
            timeout: Timeout in milliseconds
            
        Returns:
            Page object if successful, None otherwise
        """
        page = None
        try:
            page = await self.browser.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            return page
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Clean up page if it was created
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            raise
        except PlaywrightTimeoutError:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            return None
        except Exception:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            return None
    
    async def extract_links(self, page: Page, base_url: str) -> List[str]:
        """Extract all links from the current page.
        
        Args:
            page: Playwright page object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of normalized URLs (same domain only)
        """
        try:
            # Get all anchor tags with href attributes
            links = await page.evaluate("""
                () => {
                    const anchors = Array.from(document.querySelectorAll('a[href]'));
                    return anchors.map(a => a.href);
                }
            """)
            
            # Normalize and filter links
            valid_links = []
            for link in links:
                normalized = self.url_manager.normalize_and_filter(link, base_url)
                if normalized:
                    valid_links.append(normalized)
            
            return valid_links
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise cancellation
            raise
        
        except Exception:
            return []
    
    async def get_page_title(self, page: Page) -> str:
        """Get page title.
        
        Args:
            page: Playwright page object
            
        Returns:
            Page title or empty string
        """
        try:
            title = await page.title()
            return title.strip() if title else ""
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise cancellation
            raise
        
        except Exception:
            return ""
    
    async def close_page(self, page: Optional[Page]):
        """Close a page.
        
        Args:
            page: Page to close
        """
        if not page:
            return
        
        try:
            await page.close()
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise cancellation
            raise
        except Exception:
            # Ignore errors when closing pages (page may already be closed)
            pass

