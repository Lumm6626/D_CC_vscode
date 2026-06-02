"""File converter main server class."""

import os
import uuid
from typing import Dict, List

from .pdf_merger import PdfMerger
from .image_converter import ImageConverter


class FileConverter:
    """Main class for file conversion operations."""

    def __init__(self, output_dir: str = None):
        """
        Initialize FileConverter.

        Args:
            output_dir: Directory for output files. Defaults to ./output
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), 'output')
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self._pdf_merger = PdfMerger()
        self._image_converter = ImageConverter()

    def merge_pdfs(self, pdf_paths: List[str], output_filename: str = None) -> Dict:
        """
        Merge multiple PDF files into one.

        Args:
            pdf_paths: List of PDF file paths to merge
            output_filename: Optional output filename

        Returns:
            Dict with merge result
        """
        if not pdf_paths:
            return {'success': False, 'error': 'No PDF files provided'}

        if output_filename is None:
            output_filename = f'merged_{uuid.uuid4().hex[:8]}.pdf'

        output_path = os.path.join(self.output_dir, output_filename)

        merger = PdfMerger()
        for pdf_path in pdf_paths:
            if os.path.exists(pdf_path):
                merger.add_pdf(pdf_path)

        result = merger.merge(output_path)
        result['output_filename'] = output_filename
        return result

    def merge_images_to_pdf(self, image_paths: List[str], output_filename: str = None,
                             layout: str = "single") -> Dict:
        """
        Merge multiple images into a PDF.

        Args:
            image_paths: List of image file paths
            output_filename: Optional output filename
            layout: Layout mode - "single", "2x2", "3x3"

        Returns:
            Dict with conversion result
        """
        if not image_paths:
            return {'success': False, 'error': 'No image files provided'}

        if output_filename is None:
            output_filename = f'merged_{uuid.uuid4().hex[:8]}.pdf'

        output_path = os.path.join(self.output_dir, output_filename)

        return self._image_converter.images_to_pdf(image_paths, output_path, layout)

    def merge_images_to_jpg(self, image_paths: List[str], output_filename: str = None) -> Dict:
        """
        Merge multiple images into a single JPG file.

        Args:
            image_paths: List of image file paths
            output_filename: Optional output filename

        Returns:
            Dict with conversion result
        """
        if not image_paths:
            return {'success': False, 'error': 'No image files provided'}

        if output_filename is None:
            output_filename = f'merged_{uuid.uuid4().hex[:8]}.jpg'

        output_path = os.path.join(self.output_dir, output_filename)

        return self._image_converter.images_to_jpg(image_paths, output_path)