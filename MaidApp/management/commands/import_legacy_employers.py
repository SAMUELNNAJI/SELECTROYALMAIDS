"""Import legacy employer requests from the old site's MySQL dump.

Usage:
    python manage.py import_legacy_employers [path/to/request.sql]

The dump's `request` table (selectro_new.request) holds every employer that
requested a maid on the previous website. Rows are upserted into
MaidApp.LegacyEmployer keyed by the original `request.id`, so the command is
safe to re-run. Bot/spam submissions are flagged with is_spam instead of being
dropped, and maids named in the legacy 'assigned' column are linked when they
are not already placed with someone else.
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from MaidApp.models import LegacyEmployer, MaidProfile

# Column order used by every INSERT INTO `request` statement in the dump.
COLUMNS = [
    'id', 'fname', 'lname', 'phone', 'email', 'homeaddress', 'profession',
    'company', 'companyaddress', 'familymembers', 'typeofapartment',
    'marital', 'maidgender', 'reqservice', 'howsoon', 'subplan', 'assigned',
]

# Markers for the bot/scraper submissions polluting the legacy table.
SPAM_NAME_TOKENS = (
    'hfjnulyz', 'forexlax', 'login97', 'login51', 'prubrebag',
    'unombig', 'padvarm', 'burenokseils', 'chapligatup', 'acunetix',
)
SPAM_EMAIL_MARKERS = (
    'pochtampt.com', 'mailnest.xyz', 'baileymail.xyz', 'eewmaop.com',
    'mailbox.in.ua', 'twitch.work', 'lmaill.xyz', 'email.tst',
)


def looks_like_spam(row):
    """Heuristic flag for the automated junk rows in the legacy dump."""
    name_blob = f"{row.get('fname', '')} {row.get('lname', '')}".lower()
    if any(token in name_blob for token in SPAM_NAME_TOKENS):
        return True
    email = row.get('email', '').lower()
    if any(marker in email for marker in SPAM_EMAIL_MARKERS):
        return True
    first = row.get('fname', '')
    if 'http' in first.lower() or first.startswith('* * *') or 'notification' in first.lower():
        return True
    return False


INSERT_RE = re.compile(r"INSERT INTO `request`\s*\([^)]*\)\s*VALUES", re.IGNORECASE)


def _parse_tuple(text, i):
    """Parse one `(...)` tuple starting after its '('. Returns (values, next_i)."""
    values, buf, in_string = [], [], False
    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == '\\':
                if i + 1 < len(text):
                    mapped = {'n': '\n', 'r': '\r', 't': '\t', '0': '\0', 'Z': '\x1a'}.get(text[i + 1], text[i + 1])
                    buf.append(mapped)
                    i += 2
                    continue
                i += 1
                continue
            if ch == "'":
                if i + 1 < len(text) and text[i + 1] == "'":  # '' escaped quote
                    buf.append("'")
                    i += 2
                    continue
                in_string = False
                i += 1
                continue
            buf.append(ch)
            i += 1
            continue
        if ch == "'":
            in_string = True
            buf = []  # discard any whitespace between the comma and the quote
            i += 1
            continue
        if ch == ',':
            values.append(''.join(buf))
            buf = []
            i += 1
            continue
        if ch == ')':
            values.append(''.join(buf))
            return values, i + 1
        buf.append(ch)
        i += 1
    return None, i


def parse_rows(text):
    """Yield a dict per row found in every `INSERT INTO `request` ... VALUES` statement."""
    pos = 0
    while True:
        match = INSERT_RE.search(text, pos)
        if not match:
            return
        i = match.end()
        while i < len(text):
            while i < len(text) and text[i] in ' \r\n\t':
                i += 1
            if i >= len(text) or text[i] != '(':
                break
            values, i = _parse_tuple(text, i + 1)
            if values is None:
                return
            yield dict(zip(COLUMNS, (values + [''] * len(COLUMNS))[:len(COLUMNS)]))
            while i < len(text) and text[i] in ' \r\n\t':
                i += 1
            if i < len(text) and text[i] == ',':
                i += 1
                continue
            break
        pos = i


class Command(BaseCommand):
    help = 'Import legacy employer requests from a request.sql MySQL dump into LegacyEmployer.'

    def add_arguments(self, parser):
        parser.add_argument('sql_file', nargs='?', default='request.sql',
                            help='Path to the request.sql dump (default: request.sql)')

    def handle(self, *args, **options):
        path = Path(options['sql_file'])
        if not path.exists():
            raise CommandError(f'File not found: {path}')
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('cp1252', errors='replace')

        created = updated = linked = spam = 0
        for row in parse_rows(text):
            try:
                legacy_id = int((row.get('id') or '0').strip() or 0)
            except ValueError:
                continue
            if not legacy_id:
                continue

            defaults = dict(
                first_name=row.get('fname', ''),
                last_name=row.get('lname', ''),
                phone=row.get('phone', ''),
                email=row.get('email', ''),
                home_address=row.get('homeaddress', ''),
                profession=row.get('profession', ''),
                company=row.get('company', ''),
                company_address=row.get('companyaddress', ''),
                family_members=row.get('familymembers', ''),
                apartment_type=row.get('typeofapartment', ''),
                marital_status=row.get('marital', ''),
                maid_gender=row.get('maidgender', ''),
                requested_service=row.get('reqservice', ''),
                how_soon=row.get('howsoon', ''),
                plan=(row.get('subplan') or 'premium').strip().lower() or 'premium',
                assigned=row.get('assigned', ''),
                is_spam=looks_like_spam(row),
            )
            if defaults['is_spam']:
                spam += 1
            obj, was_created = LegacyEmployer.objects.update_or_create(
                legacy_id=legacy_id, defaults=defaults)
            if was_created:
                created += 1
                # Link the maid recorded in the legacy 'assigned' column, but
                # never steal a maid that is already placed with someone else.
                reg = obj.assigned_reg_number
                if reg:
                    maid = MaidProfile.objects.filter(reg_number__iexact=reg).first()
                    if (maid and not maid.assigned_employer_id
                            and not maid.assigned_legacy_employer_id
                            and maid.assign_status != 'assigned'):
                        maid.assign_status = 'assigned'
                        maid.assigned_legacy_employer = obj
                        try:
                            maid.save()
                            linked += 1
                        except ValueError:
                            self.stdout.write(self.style.WARNING(
                                f'Could not link maid {reg} to legacy employer #{legacy_id}: capacity.'))
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Import finished: {created} created, {updated} updated, '
            f'{spam} flagged as spam, {linked} maid(s) auto-linked from legacy assignments.'))
