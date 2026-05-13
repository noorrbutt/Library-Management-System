from datetime import datetime, timedelta


def get_expiry():
    return datetime.today() + timedelta(days=15)
