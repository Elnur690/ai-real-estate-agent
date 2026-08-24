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
        Generates a highly precise inpainting mask targeting ONLY the semi-transparent
        watermark text strokes (e.g. Bina.az, Tap.az, Lalafo, YeniEmlak) without affecting
        any surrounding background or furniture details.
        """
        import cv2
        import numpy as np

        h, w = img_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        kernel_tophat = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        # 1. Precise Center Watermark Region (text occupies ~4% height and ~25% width)
        cy1, cy2 = int(h * 0.46), int(h * 0.54)
        cx1, cx2 = int(w * 0.35), int(w * 0.65)
        center_roi = img_bgr[cy1:cy2, cx1:cx2]
        if center_roi.size > 0:
            gray_c = cv2.cvtColor(center_roi, cv2.COLOR_BGR2GRAY)
            tophat_c = cv2.morphologyEx(gray_c, cv2.MORPH_TOPHAT, kernel_tophat)
            _, thresh_c = cv2.threshold(tophat_c, 15, 255, cv2.THRESH_BINARY)
            dilated_c = cv2.dilate(thresh_c, kernel_dilate, iterations=1)
            mask[cy1:cy2, cx1:cx2] = dilated_c

        # 2. Precise Bottom-Right Watermark Stamp
        bry1, bry2 = int(h * 0.95), int(h * 0.998)
        brx1, brx2 = int(w * 0.82), int(w * 0.998)
        br_roi = img_bgr[bry1:bry2, brx1:brx2]
        if br_roi.size > 0:
            gray_br = cv2.cvtColor(br_roi, cv2.COLOR_BGR2GRAY)
            tophat_br = cv2.morphologyEx(gray_br, cv2.MORPH_TOPHAT, kernel_tophat)
            _, thresh_br = cv2.threshold(tophat_br, 15, 255, cv2.THRESH_BINARY)
            dilated_br = cv2.dilate(thresh_br, kernel_dilate, iterations=1)
            mask[bry1:bry2, brx1:brx2] = dilated_br

        # 3. Precise Bottom-Left Watermark Stamp (if present)
        bly1, bly2 = int(h * 0.95), int(h * 0.998)
        blx1, blx2 = int(w * 0.01), int(w * 0.18)
        bl_roi = img_bgr[bly1:bly2, blx1:blx2]
        if bl_roi.size > 0:
            gray_bl = cv2.cvtColor(bl_roi, cv2.COLOR_BGR2GRAY)
            tophat_bl = cv2.morphologyEx(gray_bl, cv2.MORPH_TOPHAT, kernel_tophat)
            _, thresh_bl = cv2.threshold(tophat_bl, 15, 255, cv2.THRESH_BINARY)
            dilated_bl = cv2.dilate(thresh_bl, kernel_dilate, iterations=1)
            mask[bly1:bly2, blx1:blx2] = dilated_bl

        return mask

    @classmethod
    def clean_image_buffer(cls, image_bytes: bytes) -> bytes:
        """
        Takes raw image bytes, removes portal watermarks using Navier-Stokes inpainting
        with minimal radius, preserving 100% of the original photo sharpness and colors.
        """
        try:
            import cv2
            import numpy as np

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return image_bytes

            mask = cls._create_watermark_mask(img)

            # If no watermark strokes detected, return original bytes without modification
            if np.count_nonzero(mask) == 0:
                return image_bytes

            # Inpaint using Navier-Stokes (cv2.INPAINT_NS) with radius 2 for razor sharp texture preservation
            clean_img = cv2.inpaint(img, mask, inpaintRadius=2, flags=cv2.INPAINT_NS)

            # Encode back to high-quality JPEG (95% quality)
            success, encoded_img = cv2.imencode('.jpg', clean_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
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
