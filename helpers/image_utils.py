"""Utility functions for resizing images stored as base64 data URIs."""

import base64
import io
import urllib.request

from PIL import Image

IMAGE_VARIANT_SIZES = (16, 32, 64)

# Limit download size to 5 MB to prevent abuse.
_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024


def _data_uri_to_pil(data_uri):
    """Decode a base64 data URI into a Pillow Image."""
    _header, b64data = data_uri.split(",", 1)
    image_bytes = base64.b64decode(b64data)
    return Image.open(io.BytesIO(image_bytes))


def _pil_to_data_uri(img):
    """Encode a Pillow Image as a PNG base64 data URI."""
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


def resize_data_uri(data_uri, size):
    """Resize a data-URI image to a *size* x *size* square (PNG)."""
    img = _data_uri_to_pil(data_uri)
    img = img.convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    return _pil_to_data_uri(img)


def generate_image_variants(data_uri):
    """Return a dict ``{16: data_uri, 32: …, 64: …}`` from a 128×128 source."""
    img = _data_uri_to_pil(data_uri).convert("RGBA")
    variants = {}
    for size in IMAGE_VARIANT_SIZES:
        resized = img.resize((size, size), Image.LANCZOS)
        variants[size] = _pil_to_data_uri(resized)
    return variants


def download_image_to_data_uri(url):
    """Download an image from *url*, resize to 128×128, and return a PNG data URI.

    Raises ``ValueError`` on download or image-processing errors.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "OpenGRC/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            content_length = resp.headers.get("Content-Length")
            if content_length and int(content_length) > _MAX_DOWNLOAD_BYTES:
                raise ValueError("Image too large (max 5 MB).")
            data = resp.read(_MAX_DOWNLOAD_BYTES + 1)
            if len(data) > _MAX_DOWNLOAD_BYTES:
                raise ValueError("Image too large (max 5 MB).")
    except urllib.error.URLError as exc:
        raise ValueError(f"Failed to download image: {exc}") from exc

    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA")
        img = img.resize((128, 128), Image.LANCZOS)
    except Exception as exc:
        raise ValueError(f"Invalid image data: {exc}") from exc

    return _pil_to_data_uri(img)
