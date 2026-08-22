"""
ZeptoMail HTTP API email backend.

Use this instead of SMTP when the hosting provider blocks outbound mail
ports (25 / 465 / 587). The ZeptoMail REST API travels over plain HTTPS
port 443, which is never blocked.

Setup (environment variables):
    EMAIL_BACKEND       = selectroyal.zeptomail_backend.ZeptoMailAPIBackend
    EMAIL_HOST_PASSWORD = <ZeptoMail "Send Mail" token>   # sent as Bearer key
    DEFAULT_FROM_EMAIL  = info@selectroyalmaids.com.ng    # must be a verified
                                                          # ZeptoMail sender
"""
import base64
import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

API_URL = 'https://api.zeptomail.com/v1.1/email'


def _addr(entry):
    """Normalise a Django recipient (string or 2/3-tuple) to ZeptoMail JSON."""
    if isinstance(entry, str):
        return {'email_address': {'address': entry}}
    name, address = entry[0], entry[1]
    return {'email_address': {'address': address, 'name': name}}


class ZeptoMailAPIBackend(BaseEmailBackend):
    """Delivers Django EmailMessage objects through ZeptoMail's REST API."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            try:
                if self._deliver(message):
                    sent += 1
            except Exception:
                logger.exception('ZeptoMail API delivery failed for %r',
                                 message.subject)
                if not self.fail_silently:
                    raise
        return sent

    def _deliver(self, msg):
        payload = {
            'from': _addr(msg.from_email),
            'to': [_addr(r) for r in msg.to],
            'subject': msg.subject,
        }
        if getattr(msg, 'cc', None):
            payload['cc'] = [_addr(r) for r in msg.cc]
        if getattr(msg, 'bcc', None):
            payload['bcc'] = [_addr(r) for r in msg.bcc]
        if getattr(msg, 'reply_to', None):
            payload['reply_to'] = [_addr(r) for r in msg.reply_to]

        # Plain-text body
        if msg.body:
            payload['textbody'] = msg.body

        # HTML alternative (Django stores alternatives as [(content, mimetype)])
        for content, mimetype in getattr(msg, 'alternatives', []):
            if mimetype == 'text/html':
                payload['htmlbody'] = content
                break

        # Attachments: (filename, content, mimetype) tuples or MIMEBase objects
        attachments = []
        for att in getattr(msg, 'attachments', []):
            if isinstance(att, tuple):
                filename, content = att[0], att[1]
            else:
                filename = att.get_filename() or 'attachment'
                content = att.get_payload(decode=True) or b''
            attachments.append({
                'name': filename,
                'content': base64.b64encode(content).decode('ascii'),
            })
        if attachments:
            payload['attachments'] = attachments

        resp = requests.post(
            API_URL,
            headers={
                'Authorization': f'Bearer {settings.EMAIL_HOST_PASSWORD}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            },
            data=json.dumps(payload),
            timeout=20,
        )
        if resp.status_code not in (200, 201):
            logger.error('ZeptoMail API error %s: %s', resp.status_code,
                         resp.text[:500])
            if not self.fail_silently:
                raise RuntimeError(
                    f'ZeptoMail API error {resp.status_code}: {resp.text[:200]}')
            return False
        return True