import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'selectroyal.settings')
import django
django.setup()

from MaidApp.emails import send_contact_email, send_contact_ack_email

result = send_contact_email(
    first_name='Test',
    last_name='User',
    email='test@example.com',
    phone='08012345678',
    city='Lagos',
    source='Google Search',
    subject='hiring',
    message='This is a test message from verify_contact.py'
)
print('Company email sent:', result)

ack = send_contact_ack_email('Test', 'test@example.com', 'hiring')
print('Acknowledgement sent:', ack)
