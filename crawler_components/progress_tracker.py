"""This file reports progress and errors of the crawler process."""
from typing import List, Optional
import sys


class ProgressTracker:
    """Tracks progress and logs errors during crawling."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.processed_count = 0
        self.total_count = 0
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.errors: List[str] = []
        
    def set_total(self, total: int):
        """Set total number of pages to process.
        
        Args:
            total: Total number of pages
        """
        self.total_count = total
    
    def start_processing(self, url: str, worker_id: Optional[int] = None, 
                        active_workers: Optional[int] = None):
        """Update progress when starting to process a URL.
        
        Args:
            url: URL being processed
            worker_id: Optional worker ID for parallel processing
            active_workers: Optional number of active workers
        """
        self.processed_count += 1
        progress_str = self._format_progress()
        
        # Add worker info if provided
        worker_info = ""
        if worker_id is not None:
            worker_info = f"[Worker-{worker_id}] "
        if active_workers is not None:
            worker_info += f"(Active: {active_workers}) "
        
        print(f"{progress_str} {worker_info}Processing: {url}", end='\r', file=sys.stderr)
        sys.stderr.flush()
    
    def finish_processing(self, url: str, success: bool = True, error: Optional[str] = None,
                         worker_id: Optional[int] = None, active_workers: Optional[int] = None,
                         status: str = 'created'):
        """Update progress when finishing processing a URL.
        
        Args:
            url: URL that was processed
            success: Whether processing was successful
            error: Error message if processing failed
            worker_id: Optional worker ID for parallel processing
            active_workers: Optional number of active workers
            status: Processing status ('created', 'updated', 'skipped', 'unchanged', 'failed')
        """
        progress_str = self._format_progress()
        
        # Add worker info if provided
        worker_info = ""
        if worker_id is not None:
            worker_info = f"[Worker-{worker_id}] "
        if active_workers is not None:
            worker_info += f"(Active: {active_workers}) "
        
        if success:
            if status == 'created':
                self.created_count += 1
                action = "Created"
            elif status == 'updated':
                self.updated_count += 1
                action = "Updated"
            elif status in ('skipped', 'unchanged'):
                self.skipped_count += 1
                action = "Skipped"
            else:
                action = "Completed"
                
            print(f"{progress_str} {worker_info}{action}: {url}", file=sys.stderr)
        else:
            error_msg = f"{progress_str} {worker_info}Failed: {url}"
            if error:
                error_msg += f" - {error}"
            print(error_msg, file=sys.stderr)
            self.errors.append(error_msg)
        sys.stderr.flush()
    
    def _format_progress(self) -> str:
        """Format progress string.
        
        Returns:
            Formatted progress string like "[5/20]"
        """
        if self.total_count == 0:
            return f"[{self.processed_count}/?]"
        return f"[{self.processed_count}/{self.total_count}]"
    
    def log_error(self, url: str, error: str):
        """Log an error.
        
        Args:
            url: URL where error occurred
            error: Error message
        """
        error_msg = f"Error processing {url}: {error}"
        self.errors.append(error_msg)
        print(f"ERROR: {error_msg}", file=sys.stderr)
    
    def print_summary(self):
        """Print final summary of crawling process."""
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Summary:", file=sys.stderr)
        print(f"  Processed: {self.processed_count} pages", file=sys.stderr)
        print(f"  - Created: {self.created_count}", file=sys.stderr)
        print(f"  - Updated: {self.updated_count}", file=sys.stderr)
        print(f"  - Skipped: {self.skipped_count}", file=sys.stderr)
        if self.errors:
            print(f"  Errors: {len(self.errors)}", file=sys.stderr)
            print(f"\nErrors:", file=sys.stderr)
            for error in self.errors:
                print(f"  - {error}", file=sys.stderr)
        else:
            print(f"  Errors: 0", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
    
    def get_processed_count(self) -> int:
        """Get number of processed pages.
        
        Returns:
            Number of processed pages
        """
        return self.processed_count
    
    def get_error_count(self) -> int:
        """Get number of errors.
        
        Returns:
            Number of errors
        """
        return len(self.errors)

