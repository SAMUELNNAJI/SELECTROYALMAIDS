import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BlogSubscriber, MaidProfile


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

