"""
Flutterwave v4 API client for direct card charges.

Implements the officially documented v4 flow:
  1. OAuth2 client-credentials access token (10-minute lifetime, cached).
  2. AES-256-GCM field encryption using the account Encryption Key
     (key = base64-decoded, nonce = 12 random alphanumeric chars used as IV).
  3. POST /charges with inline encrypted card + customer email.
  4. PUT /charges/{id} to submit PIN/OTP authorization.
  5. GET /charges/{id} to verify final charge status.

Docs: https://developer.flutterwave.com/docs/charging-a-card
      https://developer.flutterwave.com/docs/encryption
"""

import base64
import logging
import secrets
import string
import threading
import time

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15          # seconds
TOKEN_REFRESH_MARGIN = 60     # refresh this many seconds before actual expiry


class FlutterwaveError(Exception):
    """Raised when any Flutterwave v4 API interaction fails."""


# ── Access-token cache (per web-worker process) ───────────────────────────────
_token_lock = threading.Lock()
_token_cache = {'token': '', 'expires_at': 0.0}


def reset_token_cache():
    """Forget the cached OAuth token (used by tests and after auth errors)."""
    with _token_lock:
        _token_cache['token'] = ''
        _token_cache['expires_at'] = 0.0


def get_access_token():
    """
    Return a valid Bearer token, requesting a new one only when the cached
    copy is within TOKEN_REFRESH_MARGIN seconds of expiring.
    """
    with _token_lock:
        if _token_cache['token'] and time.time() < _token_cache['expires_at']:
            return _token_cache['token']

    try:
        resp = requests.post(
            settings.FLW_TOKEN_URL,
            data={
                'client_id': settings.FLW_CLIENT_ID,
                'client_secret': settings.FLW_CLIENT_SECRET,
                'grant_type': 'client_credentials',
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception('Flutterwave token request failed.')
        raise FlutterwaveError('Unable to reach the payment gateway.') from exc

    if resp.status_code != 200:
        logger.error('Flutterwave token rejected: %s %s', resp.status_code, resp.text[:300])
        raise FlutterwaveError('Payment gateway authentication failed. Please contact support.')

    payload = resp.json()
    token = payload.get('access_token', '')
    expires_in = int(payload.get('expires_in', 600))
    if not token:
        raise FlutterwaveError('Payment gateway returned an empty token.')

    with _token_lock:
        _token_cache['token'] = token
        _token_cache['expires_at'] = time.time() + max(expires_in - TOKEN_REFRESH_MARGIN, 30)
    return token


# ── AES-256-GCM field encryption ──────────────────────────────────────────────
_NONCE_ALPHABET = string.ascii_letters + string.digits


def generate_nonce(length=12):
    """Random alphanumeric nonce — exactly 12 characters per FLW spec."""
    return ''.join(secrets.choice(_NONCE_ALPHABET) for _ in range(length))


def encrypt_field(plain_text, nonce=None):
    """
    Encrypt one sensitive field with AES-256-GCM.
    Key  = base64-decoded FLUTTERWAVE_ENCRYPT_KEY
    IV   = raw ASCII bytes of the shared 12-char nonce
    Out  = base64(ciphertext || 128-bit GCM tag)
    """
    if not plain_text:
        raise FlutterwaveError('Nothing to encrypt.')
    key_b64 = settings.FLUTTERWAVE_ENCRYPT_KEY
    if not key_b64:
        raise FlutterwaveError('Payment gateway is not configured (missing encryption key).')
    if nonce is None:
        nonce = generate_nonce()
    aes_key = base64.b64decode(key_b64)
    cipher_text = AESGCM(aes_key).encrypt(nonce.encode(), str(plain_text).encode(), None)
    return base64.b64encode(cipher_text).decode()


# ── Low-level request helpers ─────────────────────────────────────────────────
def _headers():
    return {
        'Authorization': 'Bearer ' + get_access_token(),
        'Content-Type': 'application/json',
    }


def _request(method, path, json_body=None):
    url = settings.FLW_API_BASE_URL.rstrip('/') + path
    try:
        resp = requests.request(method, url, headers=_headers(), json=json_body, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.exception('Flutterwave %s %s failed.', method, path)
        raise FlutterwaveError('Unable to connect to the payment gateway. Please try again.') from exc

    try:
        payload = resp.json()
    except ValueError:
        payload = {}

    if resp.status_code >= 400:
        err = payload.get('error') or {}
        message = (
            err.get('message')
            or payload.get('message')
            or ('Payment gateway error (%d).' % resp.status_code)
        )
        logger.warning('Flutterwave %s %s -> %s: %s', method, path, resp.status_code, message)

        # A rejected/expired token is refreshed automatically on the next attempt.
        if resp.status_code in (401, 403):
            reset_token_cache()
        raise FlutterwaveError(message)

    data = payload.get('data')
    return data if isinstance(data, dict) else {}


# ── Public API operations ─────────────────────────────────────────────────────
def create_card_charge(*, reference, amount, email, redirect_url,
                       card_number, expiry_month, expiry_year, cvv,
                       currency='NGN'):
    """
    Create a v4 charge for a card, encrypting every sensitive field with one
    shared nonce (mirrors Flutterwave's official encryption example).
    Returns the raw charge `data` dict from POST /charges.
    """
    nonce = generate_nonce()
    payload = {
        'reference': reference,
        'amount': int(amount),
        'currency': currency,
        'redirect_url': redirect_url,
        'customer': {'email': email},
        'payment_method': {
            'type': 'card',
            'card': {
                'nonce': nonce,
                'encrypted_card_number': encrypt_field(card_number, nonce),
                'encrypted_expiry_month': encrypt_field(expiry_month, nonce),
                'encrypted_expiry_year': encrypt_field(expiry_year, nonce),
                'encrypted_cvv': encrypt_field(cvv, nonce),
            },
        },
    }
    return _request('POST', '/charges', payload)


def authorize_charge(charge_id, auth_type, value):
    """
    Submit a PIN or OTP authorization for a pending charge via PUT /charges/{id}.
    PIN values must be encrypted like card fields; OTP goes as plain text.
    """
    if auth_type == 'pin':
        nonce = generate_nonce()
        authorization = {
            'type': 'pin',
            'pin': {'nonce': nonce, 'encrypted_pin': encrypt_field(value, nonce)},
        }
    else:  # otp
        authorization = {'type': 'otp', 'otp': value}
    return _request('PUT', '/charges/%s' % charge_id, {'authorization': authorization})


def retrieve_charge(charge_id):
    """Fetch the authoritative status of a charge via GET /charges/{id}."""
    return _request('GET', '/charges/%s' % charge_id)


# ── Card-input validation (format only; no Luhn/issuer checks needed here) ────
def validate_card_input(card_number, expiry_month, expiry_year, cvv):
    """
    Return an error string for malformed card input, or '' when acceptable.
    expiry_year accepts 2- or 4-digit forms ('26' or '2026').
    """
    digits = ''.join(ch for ch in str(card_number or '') if ch.isdigit())
    if not (12 <= len(digits) <= 19):
        return 'Please enter a valid card number.'
    try:
        month = int(expiry_month)
    except (TypeError, ValueError):
        return 'Please enter the card expiry month.'
    if not 1 <= month <= 12:
        return 'Expiry month must be between 01 and 12.'
    try:
        year = int(str(expiry_year))
    except (TypeError, ValueError):
        return 'Please enter the card expiry year.'
    if len(str(expiry_year).strip()) not in (2, 4):
        return 'Expiry year must be 2 or 4 digits.'
    cvv_digits = ''.join(ch for ch in str(cvv or '') if ch.isdigit())
    if not (3 <= len(cvv_digits) <= 4):
        return 'Please enter the 3 or 4 digit CVV on the card.'
    return ''
