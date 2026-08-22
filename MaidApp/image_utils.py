import os
import re
import logging
import time
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
]

ACCEPT_HEADERS = [
    'image/webp,image/apng,image/avif,image/*,*/*;q=0.8',
    'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
    'image/jpeg,image/png,image/*,*/*;q=0.8',
]


def download_external_image(url, upload_to):
    """
    Download an image from an external URL and save it to media storage.

    Tries multiple user-agent / accept header combinations, follows redirects,
    and falls back to Open Graph / Twitter meta tags for HTML pages.

    Returns the relative path of the saved file, or None if download failed.
    """
    if not url or not url.strip():
        return None

    url = url.strip()

    for attempt in range(3):
        headers = {
            'User-Agent': USER_AGENTS[attempt % len(USER_AGENTS)],
            'Accept': ACCEPT_HEADERS[attempt % len(ACCEPT_HEADERS)],
            'Accept-Language': 'en-US,en;q=0.9',
        }
        try:
            return _try_download(url, upload_to, headers)
        except Exception as exc:
            logger.warning('Download attempt %d failed for %s: %s', attempt + 1, url, exc)
            time.sleep(0.5)

    logger.warning('All download attempts failed for %s', url)
    return None


def _try_download(url, upload_to, headers):
    resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
    resp.raise_for_status()

    content_type = resp.headers.get('Content-Type', '').split(';')[0].strip()

    if content_type.startswith('image/'):
        ext = _ext_from_content_type(content_type) or _ext_from_url(url) or '.jpg'
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

    # Some CDNs return binary data with a generic content-type. If the URL
    # looks like an image path, save it anyway using the URL extension.
    if _looks_like_image_url(url):
        ext = _ext_from_url(url) or '.jpg'
        filename = _generate_filename(url, ext)
        saved_path = default_storage.save(
            os.path.join(upload_to, filename),
            ContentFile(resp.content),
        )
        logger.info('Saved image from %s (generic content-type %s) to %s', url, content_type, saved_path)
        return saved_path

    logger.warning('Unsupported content type for image download: %s from %s', content_type, url)
    return None


def _looks_like_image_url(url):
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif'))


def resolve_image_url(url, timeout=15):
    """
    Turn any URL an admin pastes into an Image URL that is directly usable as
    an <img> src.

    A lot of share links are NOT image files:
      - https://share.google/...          -> redirects to a Google *page*
      - https://unsplash.com/photos/...   -> an HTML page
      - https://photos.app.goo.gl/...     -> a Google Photos page
    Browsers cannot render HTML inside an <img>, so these all "fall back".
    The resolved HTML page still embeds an og:image tag, so we can follow
    redirects and extract the real image URL.

    Returns the resolved direct image URL; if nothing can be found the
    original URL is returned unchanged (the template then degrades to the
    icon fallback rather than erroring).
    """
    if not url or not url.strip():
        return (url or '').strip()

    url = url.strip()
    seen = set()

    for _ in range(3):
        if url in seen:
            break
        seen.add(url)
        try:
            resp = requests.get(
                url,
                headers={
                    'User-Agent': USER_AGENTS[0],
                    'Accept': ACCEPT_HEADERS[0],
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                timeout=timeout,
                allow_redirects=True,
            )
        except Exception:
            break

        content_type = resp.headers.get('Content-Type', '').split(';')[0].strip().lower()

        if content_type.startswith('image/'):
            return resp.url or url

        # Some CDNs serve images with a generic/empty Content-Type but an
        # image-looking path (e.g. .jpg). Trust that and use the final URL.
        if not content_type and _looks_like_image_url(url):
            return resp.url or url

        if content_type.startswith('text/html'):
            target = _extract_meta_image(resp.text, url)
            if target and target not in seen:
                url = target
                continue

        # content-type exists but is not an image and not HTML
        break

    return url


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
        'image/vnd.microsoft.icon': '.ico',
    }
    return mapping.get(content_type)


def _ext_from_url(url):
    parsed = urlparse(url)
    path = parsed.path
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif', '.ico'):
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
        r'<meta[^>]+property=["\']og:image:secure_url["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image:secure_url["\']',
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
