from django.db import models
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import string
import random
import uuid


def get_expiry():
    return datetime.today() + timedelta(days=15)
