import base64
import os
from datetime import timedelta
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import flutterwave
from .models import EmployerProfile, PendingSignup

# A valid random 32-byte AES-256 key (base64) so encrypt_field() works in tests.
TEST_ENCRYPTION_KEY = base64.b64encode(os.urandom(32)).decode()


def _api_response(json_data, status_code=200):
    """Build a mock `requests` Response."""
    response = Mock()
    response.status_code = status_code
    response.text = str(json_data)
    response.json.return_value = json_data
    return response


_TOKEN_RESPONSE = {'access_token': 'test-access-token', 'expires_in': 600}


@override_settings(
    SECURE_SSL_REDIRECT=False,
    FLUTTERWAVE_ENCRYPT_KEY=TEST_ENCRYPTION_KEY,
    FLW_CLIENT_ID='test-client-id',
    FLW_CLIENT_SECRET='test-client-secret',
)
class SignupAndPaymentTests(TestCase):

    def setUp(self):
        flutterwave.reset_token_cache()

    def _pending_signup(self, **overrides):
        values = {
            'email': 'employer@example.com',
            'first_name': 'Ada',
            'last_name': 'Okafor',
            'password': make_password('Strong-password-123'),
            'phone': '08000000000',
            'city': 'Lagos',
            'plan': 'standard',
            'token': 'test-payment-reference',
            'expires_at': timezone.now() + timedelta(hours=1),
        }
        values.update(overrides)
        return PendingSignup.objects.create(**values)

    def _start_session(self, pending):
        session = self.client.session
        session['pending_signup_token'] = pending.token
        session.save()

    # ── Signup ────────────────────────────────────────────────────────────────
    def test_signup_stores_hashed_password(self):
        response = self.client.post(reverse('Authentication:signup'), {
            'firstName': 'Ada',
            'lastName': 'Okafor',
            'email': 'employer@example.com',
            'password': 'Strong-password-123',
            'confirmPassword': 'Strong-password-123',
            'plan': 'standard',
        })

        self.assertJSONEqual(response.content, {'ok': True, 'redirect': reverse('Authentication:payment_page')})
        pending = PendingSignup.objects.get(email='employer@example.com')
        self.assertNotEqual(pending.password, 'Strong-password-123')
        self.assertTrue(check_password('Strong-password-123', pending.password))

    # ── Flutterwave client units ──────────────────────────────────────────────
    def test_encrypt_field_roundtrip(self):
        nonce = flutterwave.generate_nonce()
        self.assertEqual(len(nonce), 12)

        encrypted = flutterwave.encrypt_field('4111111111111111', nonce)
        aes_key = base64.b64decode(TEST_ENCRYPTION_KEY)
        plain = AESGCM(aes_key).decrypt(nonce.encode(), base64.b64decode(encrypted), None)
        self.assertEqual(plain.decode(), '4111111111111111')

    def test_validate_card_input(self):
        self.assertNotEqual(flutterwave.validate_card_input('123', '1', '2030', '123'), '')
        self.assertNotEqual(flutterwave.validate_card_input('4111111111111111', '13', '2030', '123'), '')
        self.assertNotEqual(flutterwave.validate_card_input('4111111111111111', '1', '2030', '12'), '')
        self.assertEqual(flutterwave.validate_card_input('4111 1111 1111 1111', '01', '30', '123'), '')

    @patch('Authentication.flutterwave.requests')
    def test_access_token_is_cached_between_calls(self, mock_requests):
        mock_requests.post.return_value = _api_response(_TOKEN_RESPONSE)

        first = flutterwave.get_access_token()
        second = flutterwave.get_access_token()

        self.assertEqual(first, 'test-access-token')
        self.assertEqual(second, 'test-access-token')
        self.assertEqual(mock_requests.post.call_count, 1)

    @patch('Authentication.flutterwave.requests')
    def test_api_error_raises_flutterwave_error(self, mock_requests):
        mock_requests.post.return_value = _api_response(_TOKEN_RESPONSE)
        mock_requests.request.return_value = _api_response(
            {'error': {'message': 'Unable to decrypt encrypted fields provided'}}, status_code=422,
        )

        with self.assertRaises(flutterwave.FlutterwaveError):
            flutterwave.create_card_charge(
                reference='ref-1', amount=10000, email='a@b.com', redirect_url='https://x/cb/',
                card_number='4111111111111111', expiry_month='12', expiry_year='30', cvv='123',
            )

    # ── Card checkout flow ────────────────────────────────────────────────────

    @override_settings(PAYMENT_CALLBACK_URL='https://selectroyalmaids.com.ng')
    @patch('Authentication.views.http_requests.post')
    def test_payment_redirect_uses_configured_public_callback_url(self, mock_post):
        pending = self._pending_signup()
        session = self.client.session
        session['pending_signup_token'] = pending.token
        session.save()
        gateway_response = Mock()
        gateway_response.raise_for_status.return_value = None
        gateway_response.json.return_value = {
            'status': 'success',
            'data': {'link': 'https://checkout.flutterwave.com/pay/example'},
        }
        mock_post.return_value = gateway_response

        response = self.client.post(reverse('Authentication:payment_redirect'))

        self.assertRedirects(response, 'https://checkout.flutterwave.com/pay/example', fetch_redirect_response=False)
        self.assertEqual(
            mock_post.call_args.kwargs['json']['redirect_url'],
            'https://selectroyalmaids.com.ng/payment/callback/',
        )

    @patch('Authentication.views.send_payment_success_email')
    @patch('Authentication.views.send_signup_welcome_email')
    @patch('Authentication.views.http_requests.get')
    def test_verified_flutterwave_payment_creates_account_and_redirects_to_success(
        self, mock_get, _welcome, _receipt,
    ):
        pending = self._pending_signup()
        gateway_response = Mock()
        gateway_response.raise_for_status.return_value = None
        gateway_response.json.return_value = {
            'status': 'success',
            'data': {
                'status': 'successful',
                'tx_ref': pending.token,
                'amount': 10000,
                'currency': 'NGN',
                # Flutterwave test checkout can return its own test customer email.
                'customer': {'email': 'gateway-test-customer@example.com'},
            },
        }
        mock_get.return_value = gateway_response

        response = self.client.get(reverse('Authentication:payment_callback'), {
            'status': 'successful',
            'tx_ref': pending.token,
            'transaction_id': '123456789',
        })

        self.assertRedirects(response, reverse('Authentication:payment_success'))
        user = User.objects.get(email=pending.email)
        self.assertTrue(check_password('Strong-password-123', user.password))
        self.assertEqual(user.employer_profile.payment_status, 'paid')
        self.assertEqual(user.employer_profile.payment_ref, '123456789')
        self.assertFalse(PendingSignup.objects.filter(pk=pending.pk).exists())

    @patch('Authentication.views.http_requests.get')
    def test_callback_rejects_a_mismatched_gateway_reference(self, mock_get):
        pending = self._pending_signup()
        gateway_response = Mock()
        gateway_response.raise_for_status.return_value = None
        gateway_response.json.return_value = {
            'status': 'success',
            'data': {
                'status': 'successful',
                'tx_ref': 'another-reference',
                'amount': 10000,
                'currency': 'NGN',
                'customer': {'email': pending.email},
            },
        }
        mock_get.return_value = gateway_response

        response = self.client.get(reverse('Authentication:payment_callback'), {
            'status': 'successful',
            'tx_ref': pending.token,
            'transaction_id': '123456789',
        })

        self.assertRedirects(response, reverse('Authentication:payment_failed'))
        self.assertFalse(User.objects.filter(email=pending.email).exists())

    @patch('Authentication.views.send_payment_failed_email', return_value=True)
    def test_failed_payment_sends_email_to_pending_signup(self, send_failed_email):
        pending = self._pending_signup()
        session = self.client.session
        session['pending_signup_token'] = pending.token
        session.save()

        response = self.client.get(reverse('Authentication:payment_failed'))

        self.assertEqual(response.status_code, 200)
        send_failed_email.assert_called_once()
        self.assertEqual(send_failed_email.call_args.args[0].email, pending.email)
