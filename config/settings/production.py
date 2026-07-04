"""배포용 설정 (PostgreSQL, HTTPS 강제, 관리자 MFA 강제).

이 설정은 EC2/RDS 등 실제 서버에서 사용합니다. (6단계 배포 가이드와 함께)
모든 민감 값은 환경변수(.env)에서 읽으며, 없으면 '기동 실패'하도록 하여
잘못된 기본값으로 배포되는 것을 막습니다.
"""
from .base import *  # noqa: F401,F403

# --- 필수 비밀값: 환경변수 없으면 예외 발생(기본값 허용 안 함) ----------------
SECRET_KEY = env("DJANGO_SECRET_KEY")  # noqa: F405

DEBUG = False

# 실제 서비스 도메인만 허용 (예: report.school.example.com)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")  # noqa: F405

# 관리자 MFA 강제 (관리자 계정 탈취 시 전체 실명 노출 방지)
ADMIN_REQUIRE_OTP = env.bool("ADMIN_REQUIRE_OTP", default=True)  # noqa: F405

# --- 데이터베이스: PostgreSQL (AWS RDS) -----------------------------------
# RDS 저장 암호화 활성화는 인프라(6단계 가이드)에서 켠다.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),            # noqa: F405
        "USER": env("DB_USER"),            # noqa: F405
        "PASSWORD": env("DB_PASSWORD"),    # noqa: F405
        "HOST": env("DB_HOST"),            # noqa: F405 (RDS 엔드포인트)
        "PORT": env("DB_PORT", default="5432"),  # noqa: F405
        "CONN_MAX_AGE": 60,
        # RDS 로의 연결도 TLS로 강제 (전송 구간 암호화)
        "OPTIONS": {"sslmode": env("DB_SSLMODE", default="require")},  # noqa: F405
    }
}

# --- HTTPS 강제 및 보안 헤더 ----------------------------------------------
# nginx가 앞단에서 TLS를 종단하고 X-Forwarded-Proto 헤더를 넘겨준다.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# http 요청을 https로 자동 리다이렉트
SECURE_SSL_REDIRECT = True

# 쿠키는 https에서만 전송 (세션/CSRF 쿠키 탈취 방지)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS: 브라우저가 이 도메인을 항상 https로만 접속하도록 강제
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365  # 1년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 브라우저 보호 헤더
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# 신뢰 도메인(CSRF) — https 스킴 포함해서 지정
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# 리퍼러 최소화 (외부로 URL 경로가 새지 않게)
SECURE_REFERRER_POLICY = "same-origin"
