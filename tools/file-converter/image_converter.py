"""Image converter module using Pillow."""

import os
from typing import Dict, List
from PIL import Image


class ImageConverter:
    """Handles image to PDF and image to JPG conversions."""

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif'}

    def __init__(self):
        pass

    def _validate_images(self, image_paths: List[str]) -> List[str]:
        """Validate that all files exist and are supported image formats."""
        valid_paths = []
        for path in image_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext in self.SUPPORTED_FORMATS and os.path.exists(path):
                valid_paths.append(path)
        return valid_paths

    def images_to_pdf(self, image_paths: List[str], output_path: str,
                      layout: str = "single") -> Dict:
        """
        Convert multiple images to a single PDF.

        Args:
            image_paths: List of image file paths
            output_path: Path to save the output PDF
            layout: Layout mode - "single" (one per page), "2x2", "3x3"

        Returns:
            Dict with conversion result info
        """
        valid_images = self._validate_images(image_paths)

        if not valid_images:
            return {'success': False, 'error': 'No valid images found'}

        images = [Image.open(path).convert('RGB') for path in valid_images]

        if layout == "single":
            self._images_to_pdf_single(images, output_path)
        elif layout == "2x2":
            self._images_to_pdf_grid(images, output_path, 2)
        elif layout == "3x3":
            self._images_to_pdf_grid(images, output_path, 3)
        else:
            return {'success': False, 'error': f'Unknown layout: {layout}'}

        for img in images:
            img.close()

        return {
            'success': True,
            'output_path': output_path,
            'images_processed': len(valid_images),
            'layout': layout
        }

    def _images_to_pdf_single(self, images: List[Image.Image], output_path: str):
        """Save each image as a separate page in PDF."""
        if not images:
            return

        first_image = images[0]
        remaining_images = images[1:] if len(images) > 1 else []

        first_image.save(
            output_path,
            save_all=True,
            append_images=remaining_images
        )

    def _images_to_pdf_grid(self, images: List[Image.Image], output_path: str, grid_size: int):
        """Save images as a grid layout in PDF."""
        if not images:
            return

        cell_width = 800 // grid_size
        cell_height = 1200 // grid_size
        cols = grid_size
        rows = (len(images) + cols - 1) // cols

        grid_img = Image.new('RGB', (cols * cell_width, rows * cell_height), 'white')

        for idx, img in enumerate(images):
            if img is None:
                continue

            img_resized = img.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
            x = (idx % cols) * cell_width
            y = (idx // cols) * cell_height
            grid_img.paste(img_resized, (x, y))
            img_resized.close()

        grid_img.save(output_path)
        grid_img.close()

    def images_to_jpg(self, image_paths: List[str], output_path: str) -> Dict:
        """
        Merge multiple images into a single JPG file (vertical stack).

        Args:
            image_paths: List of image file paths
            output_path: Path to save the output JPG

        Returns:
            Dict with conversion result info
        """
        valid_images = self._validate_images(image_paths)

        if not valid_images:
            return {'success': False, 'error': 'No valid images found'}

        images = [Image.open(path).convert('RGB') for path in valid_images]

        total_height = sum(img.height for img in images)
        max_width = max(img.width for img in images)

        result_img = Image.new('RGB', (max_width, total_height), 'white')

        y_offset = 0
        for img in images:
            result_img.paste(img, (0, y_offset))
            y_offset += img.height
            img.close()

        result_img.save(output_path, 'JPEG', quality=95)
        result_img.close()

        return {
            'success': True,
            'output_path': output_path,
            'images_processed': len(valid_images)
        }