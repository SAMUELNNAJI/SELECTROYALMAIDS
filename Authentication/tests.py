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

    @patch('Authentication.views.send_payment_success_email')
    @patch('Authentication.views.send_signup_welcome_email')
    @patch('Authentication.flutterwave.requests')
    def test_card_form_renders_for_pending_signup(self, mock_requests, *_mail):
        pending = self._pending_signup()
        self._start_session(pending)

        response = self.client.get(reverse('Authentication:payment_redirect'))

        self.assertContains(response, 'Pay With Your Card')
        self.assertContains(response, pending.email)

    @patch('Authentication.views.send_payment_success_email')
    @patch('Authentication.views.send_signup_welcome_email')
    @patch('Authentication.flutterwave.requests')
    def test_successful_card_charge_creates_account(self, mock_requests, *_mail):
        pending = self._pending_signup()
        self._start_session(pending)
        mock_requests.post.return_value = _api_response(_TOKEN_RESPONSE)
        mock_requests.request.return_value = _api_response({
            'status': 'success', 'message': 'Charge created',
            'data': {
                'id': 'chg_OK1', 'status': 'succeeded',
                'reference': pending.token, 'amount': 10000, 'currency': 'NGN',
            },
        })

        response = self.client.post(reverse('Authentication:payment_redirect'), {
            'cardNumber': '4111 1111 1111 1111',
            'expiryMonth': '12', 'expiryYear': '30', 'cvv': '123',
        })

        self.assertRedirects(response, reverse('Authentication:payment_success'))
        user = User.objects.get(email=pending.email)
        profile = user.employer_profile
        self.assertEqual(profile.payment_status, 'paid')
        self.assertEqual(profile.payment_ref, 'chg_OK1')
        self.assertFalse(PendingSignup.objects.filter(pk=pending.pk).exists())

    @patch('Authentication.views.send_payment_success_email')
    @patch('Authentication.views.send_signup_welcome_email')
    @patch('Authentication.flutterwave.requests')
    def test_pin_authorization_then_bank_redirect(self, mock_requests, *_mail):
        pending = self._pending_signup()
        self._start_session(pending)
        pin_pending = _api_response({
            'status': 'pending', 'message': 'Charge requires authorization',
            'data': {'id': 'chg_PIN1', 'status': 'pending',
                     'next_action': {'type': 'authorize', 'authorization': {'type': 'pin'}}},
        })
        needs_3ds = _api_response({
            'status': 'pending', 'message': 'Charge updated',
            'data': {'id': 'chg_PIN1', 'status': 'pending',
                     'next_action': {'type': 'redirect_url',
                                     'redirect_url': {'url': 'https://bank.example/3ds'}}},
        })
        mock_requests.post.return_value = _api_response(_TOKEN_RESPONSE)
        charge_responses = [pin_pending, needs_3ds]  # consumed in order across calls
        mock_requests.request.side_effect = lambda method, url, **kw: charge_responses.pop(0)

        shown = self.client.post(reverse('Authentication:payment_redirect'), {
            'cardNumber': '4111111111111111', 'expiryMonth': '12', 'expiryYear': '30', 'cvv': '123',
        })
        self.assertContains(shown, 'Enter Your Card PIN')
        pending.refresh_from_db()
        self.assertEqual(pending.flw_charge_id, 'chg_PIN1')

        authorized = self.client.post(reverse('Authentication:payment_authorize'), {
            'auth_type': 'pin', 'authorization_value': '1234',
        })
        self.assertRedirects(authorized, 'https://bank.example/3ds', fetch_redirect_response=False)

    @patch('Authentication.views.send_payment_success_email')
    @patch('Authentication.views.send_signup_welcome_email')
    @patch('Authentication.flutterwave.requests')
    def test_callback_verifies_charge_and_creates_account(self, mock_requests, *_mail):
        pending = self._pending_signup()
        pending.flw_charge_id = 'chg_CB1'
        pending.save()
        self._start_session(pending)
        mock_requests.post.return_value = _api_response(_TOKEN_RESPONSE)
        mock_requests.request.return_value = _api_response({
            'status': 'success', 'message': 'Charge retrieved',
            'data': {'id': 'chg_CB1', 'status': 'succeeded', 'reference': pending.token,
                     'amount': 10000, 'currency': 'NGN'},
        })

        response = self.client.get(reverse('Authentication:payment_callback'), {'tx_ref': pending.token})

        self.assertRedirects(response, reverse('Authentication:payment_success'))
        user = User.objects.get(email=pending.email)
        self.assertTrue(user.employer_profile.is_paid)
        self.assertFalse(PendingSignup.objects.filter(pk=pending.pk).exists())

    @patch('Authentication.flutterwave.requests')
    def test_callback_rejects_a_mismatched_gateway_reference(self, mock_requests):
        pending = self._pending_signup()
        pending.flw_charge_id = 'chg_CB2'
        pending.save()
        self._start_session(pending)
        mock_requests.post.return_value = _api_response(_TOKEN_RESPONSE)
        mock_requests.request.return_value = _api_response({
            'status': 'success',
            'data': {'id': 'chg_CB2', 'status': 'succeeded', 'reference': 'another-reference',
                     'amount': 10000, 'currency': 'NGN'},
        })

        response = self.client.get(reverse('Authentication:payment_callback'), {'tx_ref': pending.token})

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
