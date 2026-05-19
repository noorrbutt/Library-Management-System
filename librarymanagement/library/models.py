"""
Legacy app shell — do not add models here.

This app exists solely to preserve Django migration history. All models were
refactored into apps/core/, apps/books/, apps/students/, and apps/members/,
but those models declare app_label = 'library' so their migrations remain
anchored to this app label. Removing this app from INSTALLED_APPS or changing
app_label would require a destructive migration squash. The shell is intentionally empty.
"""

from datetime import datetime, timedelta


def get_expiry():
    return datetime.today() + timedelta(days=15)
