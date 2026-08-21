from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import EmployerProfile, PendingSignup


@override_settings(SECURE_SSL_REDIRECT=False)
class SignupAndPaymentTests(TestCase):
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
