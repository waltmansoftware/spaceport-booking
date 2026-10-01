"""Start a fresh seeded backend for Playwright; never touches the user's DB."""
import os
from pathlib import Path
import signal
import sys
import tempfile
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def stop(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, stop)
with tempfile.TemporaryDirectory(prefix='spaceport-e2e-') as directory:
    os.environ['SPACEPORT_DB'] = str(Path(directory) / 'bookings.sqlite3')
    os.environ['DJANGO_SETTINGS_MODULE'] = 'spaceport_project.settings'
    import django
    django.setup()
    from django.core.management import call_command
    from charter_app.models import Booking
    from seed import CENTRAL, generate_seed

    call_command('migrate', interactive=False, verbosity=0)
    seed_path = Path(directory) / 'seed.json'
    seed_path.write_text(json.dumps(generate_seed(
        datetime.now(CENTRAL).date(), random_seed=42)))
    call_command('load_seed', str(seed_path))
    assert 3035 <= Booking.objects.count() <= 3070
    call_command('runserver', '127.0.0.1:8011', use_reloader=False)
