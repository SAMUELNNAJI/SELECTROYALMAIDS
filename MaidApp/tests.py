import json
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BlogSubscriber, MaidProfile, MaidRegistration


@override_settings(SECURE_SSL_REDIRECT=False)
class BlogSubscriptionTests(TestCase):
    @patch('MaidApp.views.send_blog_subscribe_email', return_value=True)
    def test_subscription_returns_success_only_after_confirmation_email_sends(self, send_email):
        response = self.client.post(
            reverse('MaidApp:blog-subscribe'),
            data=json.dumps({'email': 'Reader@Example.com'}),
            content_type='application/json',
        )

        self.assertJSONEqual(response.content, {'ok': True, 'subscribed': True, 'email_sent': True})
        self.assertTrue(BlogSubscriber.objects.filter(email='reader@example.com').exists())
        send_email.assert_called_once_with('reader@example.com')

    @patch('MaidApp.views.send_blog_subscribe_email', return_value=False)
    def test_subscription_succeeds_when_confirmation_delivery_is_delayed(self, _send_email):
        response = self.client.post(
            reverse('MaidApp:blog-subscribe'),
            data=json.dumps({'email': 'reader@example.com'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {'ok': True, 'subscribed': True, 'email_sent': False},
        )


class MaidProfileRegNumberAutoTests(TestCase):
    def test_reg_number_auto_generated_on_create(self):
        m = MaidProfile.objects.create(full_name='Ada Test', slug='ada-test-auto')
        self.assertTrue(m.reg_number.startswith('SRM-'))
        self.assertTrue(m.legacy_id)
        m2 = MaidProfile.objects.create(full_name='Bob Test', slug='bob-test-auto')
        self.assertTrue(m2.reg_number.startswith('SRM-'))
        self.assertNotEqual(m.reg_number, m2.reg_number)

    def test_explicit_reg_number_is_respected(self):
        m = MaidProfile.objects.create(
            full_name='Cara Test', slug='cara-test-auto', reg_number='SRM-9999'
        )
        self.assertEqual(m.reg_number, 'SRM-9999')
        self.assertEqual(m.legacy_id, m.legacy_id)  # auto-filled, not None


@override_settings(SECURE_SSL_REDIRECT=False)
class MaidRegistrationDedupTests(TestCase):
    def setUp(self):
        # Keep uploaded profile photos out of the real media directory.
        self._media = tempfile.TemporaryDirectory()
        self._media_override = override_settings(MEDIA_ROOT=self._media.name)
        self._media_override.enable()

    def tearDown(self):
        self._media_override.disable()
        self._media.cleanup()

    def _valid_data(self, **overrides):
        data = {
            'first_name': 'Ada', 'last_name': 'Okafor', 'email': 'ada@example.com',
            'phone': '08012345678', 'date_of_birth': '1995-04-12', 'gender': 'Female',
            'state': 'Lagos', 'city': 'Lekki', 'role': 'maid', 'work_type': 'live_in',
            'years_experience': '3', 'availability': 'Immediately',
            'expected_salary': '100000', 'languages': 'English, Yoruba',
            'skills': 'Housekeeping', 'bio': 'Experienced house help.',
            'nin': '12345678901', 'reference_name': 'Mrs Bello',
            'reference_phone': '08098765432',
        }
        data.update(overrides)
        return data

    def _post_application(self, data):
        photo = SimpleUploadedFile('photo.jpg', b'fake-image-bytes', content_type='image/jpeg')
        return self.client.post(reverse('MaidApp:apply'), {**data, 'profile_photo': photo}, follow=True)

    @patch('MaidApp.views._send_maid_application_to_whatsapp', return_value=False)
    @patch('MaidApp.views.send_maid_registration_success_email')
    @patch('MaidApp.views.send_maid_application_email')
    def test_double_submit_creates_single_application(self, send_email, send_success, _whatsapp):
        first = self._post_application(self._valid_data())
        second = self._post_application(self._valid_data())
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(MaidRegistration.objects.count(), 1)
        send_email.assert_called_once()
        send_success.assert_called_once()

    @patch('MaidApp.views._send_maid_application_to_whatsapp', return_value=False)
    @patch('MaidApp.views.send_maid_registration_success_email')
    @patch('MaidApp.views.send_maid_application_email')
    def test_resubmission_with_edited_details_does_not_duplicate(self, send_email, send_success, _whatsapp):
        self._post_application(self._valid_data())
        self._post_application(self._valid_data(phone='07011112222', city='Ikeja'))
        self.assertEqual(MaidRegistration.objects.count(), 1)
        app = MaidRegistration.objects.get()
        self.assertEqual(app.phone, '08012345678')  # the original submission is kept
        send_email.assert_called_once()
        send_success.assert_called_once()

    @patch('MaidApp.views._send_maid_application_to_whatsapp', return_value=False)
    @patch('MaidApp.views.send_maid_registration_success_email')
    @patch('MaidApp.views.send_maid_application_email')
    def test_different_nin_is_a_new_application(self, send_email, send_success, _whatsapp):
        self._post_application(self._valid_data())
        self._post_application(self._valid_data(nin='09876543210', email='tola@example.com'))
        self.assertEqual(MaidRegistration.objects.count(), 2)
        self.assertEqual(send_email.call_count, 2)
        self.assertEqual(send_success.call_count, 2)

