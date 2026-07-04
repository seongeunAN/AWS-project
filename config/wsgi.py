"""WSGI 진입점 (Gunicorn 등 프로덕션 서버가 사용)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_wsgi_application()
