import os
import io
import logging
import asyncio
import httpx
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

TEMP_IMAGE_DIR = Path("/tmp/realestate_clean_images")

class ImageWatermarkRemoverService:
    @staticmethod
    def _create_watermark_mask(img_bgr) -> Any:
        """
        Generates an inpainting mask for portal watermarks (Bina.az, Tap.az, YeniEmlak.az).
        Detects centered semi-transparent text/logo and bottom-right/bottom-center badges.
        """
        import cv2
        import numpy as np

        h, w = img_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        # 1. Central Watermark Region (most common on Bina.az and Tap.az)
        # Center 35% height and 60% width
        cy_min, cy_max = int(h * 0.32), int(h * 0.68)
        cx_min, cx_max = int(w * 0.20), int(w * 0.80)

        center_roi = img_bgr[cy_min:cy_max, cx_min:cx_max]
        gray_center = cv2.cvtColor(center_roi, cv2.COLOR_BGR2GRAY)

        # Detect high gradient edges of semi-transparent watermark text
        grad_x = cv2.Sobel(gray_center, cv2.CV_16S, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_center, cv2.CV_16S, 0, 1, ksize=3)
        abs_grad_x = cv2.convertScaleAbs(grad_x)
        abs_grad_y = cv2.convertScaleAbs(grad_y)
        grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)

        _, thresh_center = cv2.threshold(grad, 28, 255, cv2.THRESH_BINARY)

        # Morphological dilation to cover text stroke thickness
        kernel_center = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated_center = cv2.dilate(thresh_center, kernel_center, iterations=2)
        mask[cy_min:cy_max, cx_min:cx_max] = dilated_center

        # 2. Bottom Badge Region (bottom 12% of image where portal stamps/logos are placed)
        by_min = int(h * 0.88)
        bx_min = int(w * 0.60) # bottom-right
        bot_roi = img_bgr[by_min:h, bx_min:w]
        gray_bot = cv2.cvtColor(bot_roi, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding for solid watermark badges
        thresh_bot = cv2.adaptiveThreshold(
            gray_bot, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        kernel_bot = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated_bot = cv2.dilate(thresh_bot, kernel_bot, iterations=1)
        mask[by_min:h, bx_min:w] = dilated_bot

        return mask

    @classmethod
    def clean_image_buffer(cls, image_bytes: bytes) -> bytes:
        """
        Takes raw image bytes, removes portal watermarks using OpenCV Telea inpainting,
        and returns clean JPEG bytes.
        """
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes

            mask = cls._create_watermark_mask(img)

            # Inpaint using Fast Marching Method (Telea)
            clean_img = cv2.inpaint(img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

            # Encode back to JPEG
            success, encoded_img = cv2.imencode('.jpg', clean_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if success:
                return encoded_img.tobytes()
            return image_bytes
        except Exception as e:
            logger.warning(f"[ImageWatermarkRemover] Inpainting fallback: {e}")
            return image_bytes

    @classmethod
    async def fetch_and_clean_listing_images(
        cls,
        image_urls: List[str],
        listing_id: int,
        max_images: int = 5
    ) -> List[str]:
        """
        Downloads up to `max_images` listing photos, cleans watermarks asynchronously,
        saves to temporary local files, and returns the file paths.
        """
        TEMP_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        clean_file_paths = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://bina.az/"
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers) as client:
            tasks = []
            for idx, url in enumerate(image_urls[:max_images]):
                tasks.append(cls._download_and_clean_single(client, url, listing_id, idx))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, str) and os.path.exists(res):
                    clean_file_paths.append(res)

        return clean_file_paths

    @classmethod
    async def _download_and_clean_single(
        cls,
        client: httpx.AsyncClient,
        url: str,
        listing_id: int,
        index: int
    ) -> Optional[str]:
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None

            clean_bytes = cls.clean_image_buffer(resp.content)
            out_file = TEMP_IMAGE_DIR / f"listing_{listing_id}_clean_{index + 1}.jpg"
            out_file.write_bytes(clean_bytes)
            return str(out_file)
        except Exception as e:
            logger.debug(f"[ImageWatermarkRemover] Error processing {url}: {e}")
            return None
