"""Bu dosya başlıktan ve URL'den güvenli PDF dosya isimleri üretir."""
import re
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Set
from unidecode import unidecode


class FileNameGenerator:
    """Generates safe PDF file names from page titles and URLs."""
    
    def __init__(self, output_dir: Path):
        """Initialize file name generator.
        
        Args:
            output_dir: Directory where PDFs will be saved
        """
        self.output_dir = output_dir
        self.used_names: Set[str] = set()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _clean_title(self, title: str) -> str:
        """Clean and normalize title for file name.
        
        Args:
            title: Page title
            
        Returns:
            Cleaned title
        """
        if not title:
            return "Untitled"
        
        # Remove extra whitespace
        title = title.strip()
        
        # Replace spaces with underscores
        title = title.replace(' ', '_')
        
        # Remove or replace special characters that are problematic in filenames
        # Keep Turkish characters but convert to ASCII-friendly versions
        title = unidecode(title)
        
        # Remove remaining special characters
        title = re.sub(r'[^\w\-_]', '', title)
        
        # Remove multiple consecutive underscores
        title = re.sub(r'_+', '_', title)
        
        # Limit length
        if len(title) > 50:
            title = title[:50]
        
        return title.strip('_')
    
    def _get_url_segment(self, url: str) -> str:
        """Extract last segment from URL path.
        
        Args:
            url: URL to extract segment from
            
        Returns:
            Last path segment or 'index' if root
        """
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            return 'index'
        
        # Get last segment
        segments = [s for s in path.split('/') if s]
        if segments:
            last_segment = segments[-1]
            # Remove file extension if present
            last_segment = os.path.splitext(last_segment)[0]
            return last_segment
        
        return 'index'
    
    def _clean_url_segment(self, segment: str) -> str:
        """Clean URL segment for file name.
        
        Args:
            segment: URL segment to clean
            
        Returns:
            Cleaned segment
        """
        # Convert to lowercase
        segment = segment.lower()
        
        # Remove special characters
        segment = re.sub(r'[^\w\-]', '', segment)
        
        # Limit length
        if len(segment) > 30:
            segment = segment[:30]
        
        return segment
    
    def generate_name(self, title: str, url: str) -> str:
        """Generate PDF file name from title and URL.
        
        Args:
            title: Page title
            url: Page URL
            
        Returns:
            PDF file name (without .pdf extension)
        """
        clean_title = self._clean_title(title)
        url_segment = self._get_url_segment(url)
        clean_segment = self._clean_url_segment(url_segment)
        
        # Combine: title_segment
        if clean_segment and clean_segment != 'index':
            file_name = f"{clean_title}_{clean_segment}"
        else:
            file_name = clean_title
        
        # Handle duplicates
        base_name = file_name
        counter = 1
        final_name = file_name
        
        while final_name in self.used_names:
            final_name = f"{base_name}_{counter}"
            counter += 1
        
        self.used_names.add(final_name)
        return final_name
    
    def get_full_path(self, file_name: str) -> Path:
        """Get full path for PDF file.
        
        Args:
            file_name: PDF file name (without extension)
            
        Returns:
            Full path to PDF file
        """
        return self.output_dir / f"{file_name}.pdf"

