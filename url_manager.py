"""URL management and domain filtering for web crawling."""
from urllib.parse import urlparse, urljoin, urlunparse
from collections import deque
from typing import Set, Deque, Optional


class URLManager:
    """Manages URL queue, visited URLs, and domain filtering."""
    
    def __init__(self, start_url: str):
        """Initialize URL manager with starting URL.
        
        Args:
            start_url: The starting URL to crawl from
        """
        self.start_url = self._normalize_url(start_url)
        self.base_domain = self._extract_domain(self.start_url)
        self.visited: Set[str] = set()
        self.processed: Set[str] = set()  # URLs that have been fully processed (PDF generated)
        self.queue: Deque[str] = deque([self.start_url])
        self.queued_urls: Set[str] = {self.start_url}  # Fast lookup for URLs in queue
        
    def _normalize_url(self, url: str) -> str:
        """Normalize URL: add protocol, remove fragment, normalize trailing slash.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        parsed = urlparse(url)
        
        # Normalize scheme and netloc to lowercase
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove fragment (#)
        # Normalize path: remove trailing slash except for root
        # Also decode any URL encoding to ensure consistency
        path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
        
        # Keep query parameters as-is (user wants different params = different PDFs)
        # But normalize by removing empty query strings
        query = parsed.query
        if not query:
            query = ''
        
        normalized = urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            query,
            ''  # Remove fragment
        ))
        
        return normalized
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            Domain (e.g., 'www.example.com')
        """
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain.
        
        Args:
            url: URL to check
            
        Returns:
            True if same domain, False otherwise
        """
        url = self._normalize_url(url)
        domain = self._extract_domain(url)
        return domain == self.base_domain
    
    def normalize_and_filter(self, url: str, base_url: str) -> Optional[str]:
        """Normalize URL and filter if it's from same domain.
        
        Args:
            url: URL to normalize and filter
            base_url: Base URL for relative URL resolution
            
        Returns:
            Normalized URL if same domain, None otherwise
        """
        # Resolve relative URLs
        absolute_url = urljoin(base_url, url)
        normalized = self._normalize_url(absolute_url)
        
        # Filter by domain
        if not self.is_same_domain(normalized):
            return None
        
        return normalized
    
    def add_url(self, url: str) -> bool:
        """Add URL to queue if not visited and same domain.
        
        Args:
            url: URL to add (should already be normalized)
            
        Returns:
            True if added, False otherwise
        """
        # Ensure URL is normalized
        normalized = self._normalize_url(url)
        
        # Check if already visited or processed
        if normalized in self.visited or normalized in self.processed:
            return False
        
        # Check domain
        if not self.is_same_domain(normalized):
            return False
        
        # Check if already in queue (using set for O(1) lookup)
        if normalized in self.queued_urls:
            return False
        
        self.queue.append(normalized)
        self.queued_urls.add(normalized)
        return True
    
    def get_next_url(self) -> Optional[str]:
        """Get next URL from queue and mark as visited.
        
        Returns:
            Next URL to process, or None if queue is empty
        """
        if not self.queue:
            return None
        
        url = self.queue.popleft()
        self.queued_urls.discard(url)  # Remove from queued set
        self.visited.add(url)
        return url
    
    def get_queue_size(self) -> int:
        """Get current queue size.
        
        Returns:
            Number of URLs in queue
        """
        return len(self.queue)
    
    def get_visited_count(self) -> int:
        """Get number of visited URLs.
        
        Returns:
            Number of visited URLs
        """
        return len(self.visited)
    
    def has_more(self) -> bool:
        """Check if there are more URLs to process.
        
        Returns:
            True if queue is not empty
        """
        return len(self.queue) > 0
    
    def is_processed(self, url: str) -> bool:
        """Check if URL has been fully processed (PDF generated).
        
        Args:
            url: URL to check (should already be normalized)
            
        Returns:
            True if processed, False otherwise
        """
        normalized = self._normalize_url(url)
        return normalized in self.processed
    
    def mark_as_processed(self, url: str) -> None:
        """Mark URL as fully processed (PDF generated).
        
        Args:
            url: URL to mark (should already be normalized)
        """
        normalized = self._normalize_url(url)
        self.processed.add(normalized)

