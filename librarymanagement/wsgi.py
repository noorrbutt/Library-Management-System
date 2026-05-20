import os
import sys
from pathlib import Path

# Add project root to sys.path so 'apps.*' imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "librarymanagement.settings")

application = get_wsgi_application()
