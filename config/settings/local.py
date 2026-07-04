"""로컬 개발용 설정 (SQLite, DEBUG=True).

이 파일은 '내 컴퓨터에서 개발할 때만' 쓰는 설정입니다.
- SECRET_KEY는 여기서는 개발 전용 임시 값을 씁니다. (배포에서는 절대 사용 금지)
  실제 배포용 비밀 값 관리는 5단계에서 .env로 분리합니다.
- 배포(production.py)에서는 PostgreSQL, HTTPS 강제 등이 켜집니다.
"""
from .base import *  # noqa: F401,F403

# 개발 전용 임시 키입니다. 배포 환경에 절대 그대로 쓰지 마세요. (5단계에서 .env로 교체)
SECRET_KEY = "django-insecure-dev-only-key-change-me-in-production"

DEBUG = True

# 로컬에서는 모든 호스트 허용 (개발 편의)
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# 로컬 DB: SQLite (설치 불필요, 파일 한 개)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
