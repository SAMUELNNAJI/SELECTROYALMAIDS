import os
import re
import logging
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


def download_external_image(url, upload_to):
    """
    Download an image from an external URL and save it to media storage.

    Handles:
    - Direct image URLs (Content-Type: image/*)
    - HTML pages that contain Open Graph / Twitter image meta tags
      (e.g. iStock, Shutterstock, Unsplash redirect pages)

    Returns the relative path of the saved file, or None if download failed.
    """
    if not url or not url.strip():
        return None

    url = url.strip()

    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': (
                'image/webp,image/apng,image/*,*/*;q=0.8'
            ),
        }

        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get('Content-Type', '').split(';')[0].strip()

        if content_type.startswith('image/'):
            ext = _ext_from_content_type(content_type) or _ext_from_url(url)
            filename = _generate_filename(url, ext)
            saved_path = default_storage.save(
                os.path.join(upload_to, filename),
                ContentFile(resp.content),
            )
            logger.info('Downloaded image from %s to %s', url, saved_path)
            return saved_path

        if content_type.startswith('text/html'):
            image_url = _extract_meta_image(resp.text, url)
            if image_url:
                return download_external_image(image_url, upload_to)

        logger.warning('Unsupported content type for image download: %s from %s', content_type, url)
        return None

    except Exception as exc:
        logger.warning('Failed to download image from %s: %s', url, exc)
        return None


def _ext_from_content_type(content_type):
    mapping = {
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'image/svg+xml': '.svg',
        'image/bmp': '.bmp',
        'image/avif': '.avif',
    }
    return mapping.get(content_type)


def _ext_from_url(url):
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif'):
        return ext
    return '.jpg'


def _generate_filename(url, ext):
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path)
    name = os.path.splitext(basename)[0]
    if not name or name in ('/', ''):
        name = 'image'
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)[:60]
    if not name:
        name = 'image'
    return f'{name}{ext}'


def _extract_meta_image(html, base_url):
    """Extract the best available image URL from HTML meta tags."""
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']image_src["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            img_url = match.group(1)
            if img_url.startswith('//'):
                return 'https:' + img_url
            if img_url.startswith('/'):
                return base_url.rstrip('/') + img_url
            return img_url
    return None
