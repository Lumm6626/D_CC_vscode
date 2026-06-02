"""PDF merger module using pypdf."""

from typing import Dict, List, Optional
from pypdf import PdfReader, PdfWriter


class PdfMerger:
    """Handles PDF file merging operations."""

    def __init__(self):
        self._writer = PdfWriter()
        self._input_files: List[str] = []

    def add_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> int:
        """
        Add a PDF file to the merger.

        Args:
            pdf_path: Path to the PDF file
            pages: Optional list of page numbers (1-indexed) to include

        Returns:
            Number of pages in the added PDF
        """
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        self._input_files.append(pdf_path)

        if pages:
            for page_num in pages:
                if 1 <= page_num <= num_pages:
                    self._writer.add_page(reader.pages[page_num - 1])
        else:
            for page in reader.pages:
                self._writer.add_page(page)

        return num_pages

    def merge(self, output_path: str) -> Dict:
        """
        Merge all added PDFs and save to output path.

        Args:
            output_path: Path to save the merged PDF

        Returns:
            Dict with merge result info
        """
        with open(output_path, 'wb') as f:
            self._writer.write(f)

        result = {
            'success': True,
            'output_path': output_path,
            'files_merged': len(self._input_files),
            'total_pages': self.get_total_pages()
        }

        self._writer = PdfWriter()
        self._input_files = []

        return result

    def get_total_pages(self) -> int:
        """Get total page count of merged PDFs."""
        if not self._input_files:
            return 0

        total = 0
        for pdf_path in self._input_files:
            reader = PdfReader(pdf_path)
            total += len(reader.pages)
        return total