"""Bu dosya tüm crawler sürecini çalıştırır ve PDF çıktılarını yönetir."""
import argparse
import asyncio
import os
import sys
import warnings
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright

# Suppress asyncio warnings about unclosed loops
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*coroutine.*was never awaited')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*unclosed.*')

# Store original exception hook
_original_excepthook = sys.excepthook

def _quiet_excepthook(exc_type, exc_value, exc_traceback):
    """Suppress certain exceptions during shutdown."""
    # Suppress KeyboardInterrupt exceptions during shutdown
    if exc_type is KeyboardInterrupt:
        return
    
    # Suppress RuntimeError about ignored coroutines
    if exc_type is RuntimeError:
        error_msg = str(exc_value).lower()
        if 'coroutine' in error_msg or 'generatorexit' in error_msg:
            return
    
    # Suppress GeneratorExit exceptions
    if exc_type is GeneratorExit:
        return
    
    # Suppress threading module exceptions during shutdown
    if exc_traceback:
        frame = exc_traceback
        while frame:
            filename = frame.tb_frame.f_code.co_filename
            # Suppress exceptions from threading.py and concurrent/futures during shutdown
            if 'threading.py' in filename or 'concurrent/futures' in filename:
                if exc_type is KeyboardInterrupt or 'shutdown' in str(exc_value).lower():
                    return
            frame = frame.tb_next
    
    # Call original handler for other exceptions
    _original_excepthook(exc_type, exc_value, exc_traceback)

# Set custom exception hook
sys.excepthook = _quiet_excepthook

from crawler_components.url_manager import URLManager
from crawler_components.web_crawler import WebCrawler
from crawler_components.pdf_generator import PDFGenerator
from crawler_components.file_name_generator import FileNameGenerator
from crawler_components.progress_tracker import ProgressTracker


class CrawlToPDF:
    """Main orchestrator for crawling and PDF generation."""
    
    def __init__(self, start_url: str, output_dir: Optional[Path] = None, 
                 workers: int = 5, delay: float = 0.5, debug: bool = False):
        """Initialize crawler.
        
        Args:
            start_url: Starting URL to crawl
            output_dir: Output directory for PDFs (optional)
            workers: Number of parallel workers (default: 5)
            delay: Delay between requests in seconds (default: 0.5)
            debug: Enable debug logging (default: False)
        """
        self.start_url = start_url
        self.url_manager = URLManager(start_url)
        self.workers = max(1, workers)  # At least 1 worker
        self.delay = max(0.0, delay)  # Non-negative delay
        self.debug = debug
        
        # Create output directory from domain if not provided
        if output_dir is None:
            domain = self.url_manager.base_domain
            folder_name = domain.replace('.', '-') + '-pdfs'
            output_dir = Path('results') / folder_name
        
        self.output_dir = output_dir
        self.file_name_generator = FileNameGenerator(output_dir)
        self.progress_tracker = ProgressTracker()
        
    async def _process_single_url(self, crawler: WebCrawler, pdf_generator: PDFGenerator, 
                                   url: str, worker_id: Optional[int] = None,
                                   active_workers: Optional[int] = None,
                                   processed_lock: Optional[asyncio.Lock] = None) -> None:
        """Process a single URL: load, extract links, generate PDF.
        
        Args:
            crawler: WebCrawler instance
            pdf_generator: PDFGenerator instance
            url: URL to process
            worker_id: Optional worker ID for logging
            active_workers: Optional number of active workers for logging
            processed_lock: Optional lock for thread-safe processed URL tracking
        """
        # Check if URL has already been processed (thread-safe check)
        if processed_lock:
            async with processed_lock:
                if self.url_manager.is_processed(url):
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} skipping already processed URL: {url}", file=sys.stderr)
                    return
        else:
            if self.url_manager.is_processed(url):
                if self.debug:
                    print(f"[DEBUG] Worker-{worker_id} skipping already processed URL: {url}", file=sys.stderr)
                return
        
        # Start processing
        self.progress_tracker.start_processing(url, worker_id, active_workers)
        
        # Update progress total (queue size + visited count)
        queue_size = self.url_manager.get_queue_size()
        processed = self.url_manager.get_visited_count()
        self.progress_tracker.set_total(processed + queue_size)
        
        # Load page
        page = await crawler.load_page(url)
        if not page:
            self.progress_tracker.finish_processing(
                url, 
                success=False, 
                error="Failed to load page",
                worker_id=worker_id,
                active_workers=active_workers
            )
            return
        
        try:
            # Get page title
            title = await crawler.get_page_title(page)
            
            # Extract links and add to queue
            links = await crawler.extract_links(page, url)
            for link in links:
                self.url_manager.add_url(link)
            
            # Update total after discovering new links
            queue_size = self.url_manager.get_queue_size()
            processed = self.url_manager.get_visited_count()
            self.progress_tracker.set_total(processed + queue_size)
            
            # Double-check if URL has been processed by another worker while we were loading the page
            if processed_lock:
                async with processed_lock:
                    if self.url_manager.is_processed(url):
                        if self.debug:
                            print(f"[DEBUG] Worker-{worker_id} skipping URL processed by another worker: {url}", file=sys.stderr)
                        self.progress_tracker.finish_processing(
                            url,
                            success=False,
                            error="Already processed by another worker",
                            worker_id=worker_id,
                            active_workers=active_workers
                        )
                        return
            else:
                if self.url_manager.is_processed(url):
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} skipping URL processed by another worker: {url}", file=sys.stderr)
                    self.progress_tracker.finish_processing(
                        url,
                        success=False,
                        error="Already processed by another worker",
                        worker_id=worker_id,
                        active_workers=active_workers
                    )
                    return
            
            # Generate PDF
            pdf_path = await pdf_generator.generate_pdf(page, title, url)
            
            # Mark as processed only if PDF was successfully generated (thread-safe)
            if pdf_path:
                if processed_lock:
                    async with processed_lock:
                        # Double-check again before marking (another worker might have processed it)
                        if not self.url_manager.is_processed(url):
                            self.url_manager.mark_as_processed(url)
                        else:
                            if self.debug:
                                print(f"[DEBUG] Worker-{worker_id} URL was processed by another worker, deleting duplicate PDF: {pdf_path}", file=sys.stderr)
                            # Delete duplicate PDF
                            try:
                                pdf_path.unlink()
                            except Exception:
                                pass
                            self.progress_tracker.finish_processing(
                                url,
                                success=False,
                                error="Already processed by another worker",
                                worker_id=worker_id,
                                active_workers=active_workers
                            )
                            return
                else:
                    self.url_manager.mark_as_processed(url)
                
                self.progress_tracker.finish_processing(url, success=True,
                                                       worker_id=worker_id,
                                                       active_workers=active_workers)
            else:
                self.progress_tracker.finish_processing(
                    url, 
                    success=False, 
                    error="Failed to generate PDF",
                    worker_id=worker_id,
                    active_workers=active_workers
                )
        
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Re-raise to be handled by outer try-except
            raise
        
        except Exception as e:
            self.progress_tracker.finish_processing(
                url, 
                success=False, 
                error=str(e),
                worker_id=worker_id,
                active_workers=active_workers
            )
        
        finally:
            await crawler.close_page(page)
    
    async def _worker(self, crawler: WebCrawler, pdf_generator: PDFGenerator, 
                      semaphore: asyncio.Semaphore, worker_id: int,
                      active_workers_counter: dict, active_workers_lock: asyncio.Lock,
                      processed_lock: asyncio.Lock) -> None:
        """Worker function that processes URLs from queue.
        
        Args:
            crawler: WebCrawler instance
            pdf_generator: PDFGenerator instance
            semaphore: Semaphore to limit concurrent URL processing
            worker_id: Unique ID for this worker
            active_workers_counter: Dictionary to track active workers count
            active_workers_lock: Lock for thread-safe counter access
            processed_lock: Lock for thread-safe processed URL tracking
        """
        if self.debug:
            print(f"[DEBUG] Worker-{worker_id} started", file=sys.stderr)
        processed_count = 0
        empty_check_count = 0
        max_empty_checks = 10  # Exit after 10 consecutive empty checks
        
        while True:
            # STEP 1: Acquire semaphore ONLY for getting URL (quick operation)
            if self.debug:
                print(f"[DEBUG] Worker-{worker_id} waiting for semaphore to get URL...", file=sys.stderr)
            url = None
            
            async with semaphore:
                if self.debug:
                    print(f"[DEBUG] Worker-{worker_id} acquired semaphore for URL fetch", file=sys.stderr)
                
                # Check if there are more URLs
                if not self.url_manager.has_more():
                    empty_check_count += 1
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} no more URLs (check {empty_check_count}/{max_empty_checks})", file=sys.stderr)
                    if empty_check_count >= max_empty_checks:
                        if self.debug:
                            print(f"[DEBUG] Worker-{worker_id} exiting after {max_empty_checks} empty checks", file=sys.stderr)
                        break
                    url = None
                else:
                    # Get next URL (inside semaphore to prevent race condition)
                    url = self.url_manager.get_next_url()
                    if not url:
                        empty_check_count += 1
                        if self.debug:
                            print(f"[DEBUG] Worker-{worker_id} got None URL (check {empty_check_count}/{max_empty_checks})", file=sys.stderr)
                        if empty_check_count >= max_empty_checks:
                            if self.debug:
                                print(f"[DEBUG] Worker-{worker_id} exiting after {max_empty_checks} empty checks", file=sys.stderr)
                            break
                    else:
                        # Reset empty check counter if we got a URL
                        empty_check_count = 0
                        processed_count += 1
                        if self.debug:
                            print(f"[DEBUG] Worker-{worker_id} got URL #{processed_count}: {url}", file=sys.stderr)
            
            # STEP 2: Process URL OUTSIDE semaphore (allows parallel processing)
            if url:
                # Increment active workers counter
                async with active_workers_lock:
                    active_workers_counter['count'] += 1
                    active_workers = active_workers_counter['count']
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} processing URL (active: {active_workers})", file=sys.stderr)
                
                try:
                    # Process the URL (semaphore is NOT held, so other workers can get URLs)
                    await self._process_single_url(
                        crawler, pdf_generator, url, worker_id, active_workers, processed_lock
                    )
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} finished processing URL", file=sys.stderr)
                except (asyncio.CancelledError, KeyboardInterrupt):
                    async with active_workers_lock:
                        active_workers_counter['count'] -= 1
                    raise
                except Exception as e:
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} error: {e}", file=sys.stderr)
                    pass
                finally:
                    async with active_workers_lock:
                        active_workers_counter['count'] -= 1
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} done, counter decremented", file=sys.stderr)
                
                # Delay between requests (after processing)
                if self.delay > 0:
                    if self.debug:
                        print(f"[DEBUG] Worker-{worker_id} delaying {self.delay}s", file=sys.stderr)
                    await asyncio.sleep(self.delay)
            else:
                # Queue was empty, wait before checking again
                wait_time = 0.2
                if self.debug:
                    print(f"[DEBUG] Worker-{worker_id} queue empty, waiting {wait_time}s", file=sys.stderr)
                await asyncio.sleep(wait_time)
        
        if self.debug:
            print(f"[DEBUG] Worker-{worker_id} finished (processed {processed_count} URLs)", file=sys.stderr)
    
    async def crawl(self):
        """Main crawling workflow with parallel workers."""
        browser = None
        try:
            async with async_playwright() as p:
                # Launch headless Chrome
                browser = await p.chromium.launch(headless=True)
                
                try:
                    crawler = WebCrawler(browser, self.url_manager)
                    pdf_generator = PDFGenerator(self.file_name_generator)
                    
                    # Create semaphore to limit concurrent URL processing
                    # This ensures maximum 'workers' URLs are processed simultaneously
                    semaphore = asyncio.Semaphore(self.workers)
                    # Counter to track active workers
                    active_workers_counter = {'count': 0}
                    active_workers_lock = asyncio.Lock()
                    # Lock for thread-safe processed URL tracking
                    processed_lock = asyncio.Lock()
                    
                    if self.debug:
                        print(f"[DEBUG] Creating {self.workers} workers with semaphore limit {self.workers}", file=sys.stderr)
                        print(f"[DEBUG] Initial queue size: {self.url_manager.get_queue_size()}", file=sys.stderr)
                        print(f"[DEBUG] Initial visited count: {self.url_manager.get_visited_count()}", file=sys.stderr)
                    
                    # Create worker tasks - each worker processes URLs from queue
                    worker_tasks = []
                    for worker_id in range(1, self.workers + 1):
                        if self.debug:
                            print(f"[DEBUG] Creating Worker-{worker_id} task", file=sys.stderr)
                        task = asyncio.create_task(
                            self._worker(crawler, pdf_generator, semaphore, worker_id,
                                       active_workers_counter, active_workers_lock, processed_lock)
                        )
                        worker_tasks.append(task)
                    
                    if self.debug:
                        print(f"[DEBUG] All {len(worker_tasks)} worker tasks created", file=sys.stderr)
                    
                    # Wait for all workers to complete
                    try:
                        await asyncio.gather(*worker_tasks, return_exceptions=True)
                    except (asyncio.CancelledError, KeyboardInterrupt):
                        # Cancel all workers
                        self.all_done = True
                        for task in worker_tasks:
                            task.cancel()
                        # Wait for cancellation to complete
                        await asyncio.gather(*worker_tasks, return_exceptions=True)
                        raise
                    
                    # Print summary
                    self.progress_tracker.print_summary()
                
                finally:
                    # Gracefully close browser
                    if browser:
                        try:
                            await browser.close()
                        except Exception:
                            # Ignore browser close errors (browser may already be closed)
                            pass
        
        except (KeyboardInterrupt, asyncio.CancelledError):
            # Handle graceful shutdown
            print("\n\n" + "="*60, file=sys.stderr)
            print("İşlem kullanıcı tarafından durduruldu.", file=sys.stderr)
            print("="*60, file=sys.stderr)
            
            # Print partial summary
            if self.progress_tracker.get_processed_count() > 0:
                print(f"\nTamamlanan sayfalar: {self.progress_tracker.get_processed_count()}", file=sys.stderr)
                print(f"PDF'ler kaydedildi: {self.output_dir}", file=sys.stderr)
            
            # Try to close browser gracefully
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            
            # Use os._exit to bypass Python's cleanup which causes threading exceptions
            # This prevents "Exception ignored" messages from threading module
            os._exit(0)
        
        except Exception as e:
            # Handle other unexpected errors
            print(f"\n\nHata oluştu: {str(e)}", file=sys.stderr)
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            raise


async def _run_crawler(crawler):
    """Run crawler with proper exception handling."""
    try:
        await crawler.crawl()
    except (KeyboardInterrupt, asyncio.CancelledError):
        # Re-raise to be handled by crawl() method
        raise
    except Exception:
        # Re-raise other exceptions
        raise


def _exception_handler(loop, context):
    """Handle unhandled exceptions in event loop (suppress cancellation errors)."""
    exception = context.get('exception')
    message = context.get('message', '')
    
    if exception:
        # Suppress cancellation and interruption errors
        if isinstance(exception, (asyncio.CancelledError, KeyboardInterrupt)):
            return
        
        # Suppress Playwright errors that occur during cancellation
        exception_str = str(exception)
        exception_type_str = type(exception).__name__
        
        if ('ERR_ABORTED' in exception_str or 
            'TargetClosedError' in exception_type_str or
            'Target page, context or browser has been closed' in exception_str or
            'coroutine ignored' in exception_str or
            'GeneratorExit' in exception_str):
            return
    
    # Suppress "Future exception was never retrieved" warnings for cancelled tasks
    if ('Future exception was never retrieved' in message or
        'Exception ignored' in message):
        return
    
    # For other exceptions, suppress them silently (they're likely cancellation-related)
    # This prevents noisy error messages during graceful shutdown
    pass


def main():
    """Main entry point."""
    try:
        parser = argparse.ArgumentParser(
            description='Crawl a website and convert all pages to PDF',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python crawl_to_pdf.py www.example.com
  python crawl_to_pdf.py https://example.com
  python crawl_to_pdf.py example.com --output my-pdfs
  python crawl_to_pdf.py example.com --workers 10 --delay 1.0
  python crawl_to_pdf.py example.com -w 3 -d 0.3
            """
        )
        
        parser.add_argument(
            'url',
            help='Starting URL to crawl (e.g., www.example.com or https://example.com)'
        )
        
        parser.add_argument(
            '--output', '-o',
            type=Path,
            help='Output directory for PDFs (default: {domain}-pdfs)'
        )
        
        parser.add_argument(
            '--workers', '-w',
            type=int,
            default=5,
            help='Number of parallel workers (default: 5)'
        )
        
        parser.add_argument(
            '--delay', '-d',
            type=float,
            default=0.5,
            help='Delay between requests in seconds (default: 0.5)'
        )
        
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )
        
        args = parser.parse_args()
        
        # Validate arguments
        if args.workers < 1:
            parser.error("Workers must be at least 1")
        if args.delay < 0:
            parser.error("Delay must be non-negative")
        
        # Create crawler and run with proper exception handling
        crawler = CrawlToPDF(args.url, args.output, workers=args.workers, delay=args.delay, debug=args.debug)
        
        # Create event loop with custom exception handler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_exception_handler(_exception_handler)
        
        try:
            loop.run_until_complete(_run_crawler(crawler))
        finally:
            # Clean shutdown: cancel all tasks and close loop properly
            try:
                # Get all pending tasks
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                
                # Cancel all pending tasks
                for task in pending:
                    task.cancel()
                
                # Wait for cancellation to complete
                if pending:
                    # Use gather with return_exceptions to avoid raising
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                
                # Give loop a chance to process cancellations
                loop.run_until_complete(asyncio.sleep(0))
            except Exception:
                # Ignore errors during cleanup
                pass
            finally:
                try:
                    # Close the loop
                    loop.close()
                except Exception:
                    pass
    
    except KeyboardInterrupt:
        # This should be caught by crawl() method, but just in case
        print("\n\nİşlem durduruldu.", file=sys.stderr)
        # Suppress threading cleanup exceptions by exiting immediately
        os._exit(0)
    
    except Exception as e:
        print(f"\nBeklenmeyen hata: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
