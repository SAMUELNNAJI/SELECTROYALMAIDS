from django.test import TestCase
from django.urls import reverse

from .models import MaidProfile


class SimilarCardRenderCheck(TestCase):
    """Temporary diagnostic: prints the redesigned Similar Profiles markup."""

    def setUp(self):
        MaidProfile.objects.create(
            legacy_id=1, reg_number='SRM-1001', slug='main-maid',
            full_name='Main Maid', photo_filename='main.jpg',
        )
        MaidProfile.objects.create(
            legacy_id=2, reg_number='SRM-1002', slug='sim-one',
            full_name='Sarah Shuma Thomas', photo_filename='sarah.jpg',
        )
        MaidProfile.objects.create(
            legacy_id=3, reg_number='SRM-1003', slug='sim-two',
            full_name='Wualaka Regina Chinenye', assign_status='assigned',
        )

    def test_print_similar_card(self):
        response = self.client.get(reverse('MaidApp:view-profile'), {'slug': 'main-maid'})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        start = html.find('<div class="vp-similar-grid">')
        print('\n=== SIMILAR GRID ===')
        print(html[start:start + 2400])
        print('=== END ===')