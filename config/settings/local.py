"""로컬 개발용 설정 (SQLite, DEBUG=True).

- SECRET_KEY/DEBUG 등은 base.py가 환경변수(.env)에서 읽으며, 없으면 dev 기본값을 씁니다.
- 로컬에서는 관리자 MFA(OTP)를 강제하지 않습니다(ADMIN_REQUIRE_OTP=False, base 기본값).
  → 인증앱 없이도 admin 로그인 테스트가 가능합니다.
- 배포(production.py)에서는 PostgreSQL, HTTPS 강제, MFA 강제가 켜집니다.
"""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# 로컬 DB: SQLite (설치 불필요, 파일 한 개)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
