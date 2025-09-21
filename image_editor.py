# image_editor.py 
# ChatGPT generated
from __future__ import annotations
import io
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Dict

from PIL import Image, ImageOps

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class ImageEditor:
    """
    Prepare a single source photo for web upload:
    - EXIF orientation fix
    - High-quality downscale (LANCZOS)
    - Save WebP + progressive JPEG under target size
    - Preserve ICC profile (avoid color shifts), strip heavy EXIF
    """

    def __init__(
        self,
        out_dir: Path | str = "optimized",
        max_long_edge: int = 1600,
        target_kb: int = 300,
        jpeg_min_quality: int = 50,
        jpeg_max_quality: int = 95,
        webp_quality_range: Tuple[int, int] = (60, 95),
        jpeg_subsampling: int = 2,        # 4:2:0 = 2 (good tradeoff for photos)
        jpeg_progressive: bool = True,
    ) -> None:
        self.out_dir = Path(out_dir)
        self.max_long_edge = max_long_edge
        self.target_bytes = target_kb * 1024
        self.jpeg_q_range = (jpeg_min_quality, jpeg_max_quality)
        self.webp_q_range = webp_quality_range
        self.jpeg_subsampling = jpeg_subsampling
        self.jpeg_progressive = jpeg_progressive

        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Public API ----------
    def prepare_for_upload(self, image_path: str | Path) -> Dict[str, Dict[str, int | str]]:
        """
        Process ONE image and write outputs to self.out_dir:
          - <name>.webp
          - <name>.jpg
        Returns a dict with output paths & chosen qualities/sizes.

        Example:
        {
          "webp": {"path": "optimized/foo.webp", "bytes": 284112, "quality": 82},
          "jpg":  {"path": "optimized/foo.jpg",  "bytes": 297003, "quality": 84}
        }
        """
        src = Path(image_path)
        im = self._load_image_safe(src)
        if im is None:
            raise FileNotFoundError(f"Could not open or decode image: {src}")

        # Convert mode for safe encoding; preserve ICC profile if present.
        icc = im.info.get("icc_profile")
        if im.mode not in ("RGB", "RGBA", "L"):
            im = im.convert("RGB")

        # Downscale with high-quality filter
        im = self._resize_for_web(im, self.max_long_edge)

        stem = src.stem
        webp_path = self.out_dir / f"{stem}.webp"
        jpg_path = self.out_dir / f"{stem}.jpg"

        webp_bytes, webp_q = self._save_under_target(
            im, webp_path, "WEBP", self.target_bytes, icc, self.webp_q_range
        )
        jpg_bytes, jpg_q = self._save_under_target(
            im, jpg_path, "JPEG", self.target_bytes, icc, self.jpeg_q_range
        )

        logging.info(
            "%s → %s (%d KB, q=%d), %s (%d KB, q=%d)",
            src.name, webp_path.name, webp_bytes // 1024, webp_q,
            jpg_path.name, jpg_bytes // 1024, jpg_q
        )

        return {
            "webp": {"path": str(webp_path), "bytes": webp_bytes, "quality": webp_q},
            "jpg":  {"path": str(jpg_path),  "bytes": jpg_bytes,  "quality": jpg_q},
        }

    # ---------- Internals ----------
    def _load_image_safe(self, path: Path) -> Optional[Image.Image]:
        try:
            im = Image.open(path)
            im.load()  # ensure decode now (catch truncation early)
            im = ImageOps.exif_transpose(im)  # apply EXIF orientation
            return im
        except Exception as e:
            logging.error("Failed to open %s: %s", path, e)
            return None

    def _resize_for_web(self, im: Image.Image, max_long_edge: int) -> Image.Image:
        w, h = im.size
        long_edge = max(w, h)
        if long_edge <= max_long_edge:
            return im
        scale = max_long_edge / long_edge
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        return im.resize(new_size, Image.LANCZOS)

    def _encode_to_bytes(
        self,
        im: Image.Image,
        fmt: str,
        quality: int,
        icc_profile: Optional[bytes],
    ) -> bytes:
        buf = io.BytesIO()
        params = {"quality": quality, "optimize": True}
        if icc_profile:
            params["icc_profile"] = icc_profile

        if fmt == "WEBP":
            params.update({"format": "WEBP", "method": 6})
            im.save(buf, **params)
        elif fmt == "JPEG":
            im_rgb = im.convert("RGB")
            params.update({
                "format": "JPEG",
                "subsampling": self.jpeg_subsampling,
                "progressive": self.jpeg_progressive,
            })
            im_rgb.save(buf, **params)
        else:
            raise ValueError("Unsupported output format")

        return buf.getvalue()

    def _binary_search_quality(
        self,
        im: Image.Image,
        fmt: str,
        target_bytes: int,
        q_lo: int,
        q_hi: int,
        icc_profile: Optional[bytes],
        max_iters: int = 12,
    ) -> Tuple[bytes, int]:
        best_data = None
        best_q = q_lo
        lo, hi = q_lo, q_hi

        for _ in range(max_iters):
            q = (lo + hi) // 2
            data = self._encode_to_bytes(im, fmt, q, icc_profile)
            size = len(data)

            if size <= target_bytes:
                best_data, best_q = data, q
                lo = q + 1
            else:
                hi = q - 1

            if lo > hi:
                break

        if best_data is not None:
            return best_data, best_q

        # Couldn’t hit target; return smallest feasible quality
        q = max(q_lo, min(q_hi, hi))
        data = self._encode_to_bytes(im, fmt, q, icc_profile)
        return data, q

    def _save_under_target(
        self,
        im: Image.Image,
        out_path: Path,
        fmt: str,
        target_bytes: int,
        icc_profile: Optional[bytes],
        q_range: Tuple[int, int],
    ) -> Tuple[int, int]:
        data, q = self._binary_search_quality(im, fmt, target_bytes, q_range[0], q_range[1], icc_profile)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        return len(data), q