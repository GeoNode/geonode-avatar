#!/usr/bin/env python

import os
import sys
import tempfile

import django
from django.conf import settings
from django.test.utils import get_runner

ROOT = os.path.abspath(os.path.dirname(__file__))
APP_ROOT = os.path.join(ROOT, '..')
sys.path.append(APP_ROOT)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'


# We do this here because settings.py has a tendency to be imported more than
# once, in certain situations, and we only want one temporary test folder.
MEDIA_ROOT = os.path.join(tempfile.gettempdir(), 'avatars')
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(os.path.join(MEDIA_ROOT, 'test'))
settings.MEDIA_ROOT = MEDIA_ROOT


if __name__ == "__main__":
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['avatar'], verbosity=1)
    if failures:
        sys.exit(failures)
