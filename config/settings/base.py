"""공통 Django 설정 (base).

로컬(local.py)과 배포(production.py)가 이 파일을 상속합니다.
- 민감 정보(SECRET_KEY, DB 비밀번호 등)는 코드에 하드코딩하지 않고
  환경변수(.env)로 읽습니다. (django-environ 사용)
- 관리자 MFA(django-otp), IP 미로깅(LOGGING) 등 보안 공통 설정을 여기 둡니다.
"""
from pathlib import Path

import environ

# 프로젝트 최상위 경로 (config/settings/base.py -> AWS-project/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- 환경변수 로딩 ---------------------------------------------------------
# .env 파일이 있으면 읽어 들인다. (없어도 동작 — 값은 아래 default 사용)
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# SECRET_KEY: 환경변수 우선. 로컬 개발 편의를 위해 dev용 기본값을 둔다.
# 배포(production.py)에서는 기본값을 허용하지 않고 반드시 환경변수를 요구한다.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-key-change-me-in-production",
)

DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# 관리자 로그인에 OTP(2단계 인증)를 강제할지 여부.
# 로컬에서는 기본 False(편의), 배포에서는 True 로 켠다.
ADMIN_REQUIRE_OTP = env.bool("ADMIN_REQUIRE_OTP", default=False)

# --- 앱 ------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # MFA (관리자 2단계 인증)
    "django_otp",
    "django_otp.plugins.otp_totp",   # 스마트폰 인증앱(TOTP)
    "django_otp.plugins.otp_static",  # 복구용 일회성 코드
    # 로컬 앱
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # OTPMiddleware 는 AuthenticationMiddleware 바로 뒤에 위치해야 한다.
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# 비밀번호 검증 (관리자 계정 보호)
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# 국제화 — 한국어/서울 시간대
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# 정적 파일
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- 로깅: 신고자 IP를 절대 남기지 않는다 --------------------------------
# 핵심: Django 기본 로깅에는 'mail_admins' 핸들러가 있어 오류 발생 시 관리자에게
# 요청 정보를 이메일로 보내는데, 여기에는 request.META(REMOTE_ADDR 등 IP)가 포함될
# 수 있다. 이는 IP 미수집 원칙에 위배되므로, 로깅을 명시적으로 재정의해
# 'IP가 포함될 수 있는 핸들러'를 제거한다.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # 로그 메시지에 IP/사용자 식별 정보를 넣지 않는다. (레벨/시각/메시지만)
        "safe": {"format": "[{levelname}] {asctime} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "safe",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # django.request 로거를 콘솔로만 보낸다 (mail_admins 미사용 = 요청 META/IP 미전송)
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# --- 보안 관련 공통 주석 ---------------------------------------------------
# * 신고자 IP는 어디에도 저장/기록하지 않는다.
#   - DB: Report 모델에 IP 필드 없음.
#   - 뷰: request.META(REMOTE_ADDR/HTTP_X_FORWARDED_FOR) 를 읽는 코드 없음.
#   - 로그: 위 LOGGING 에서 IP 포함 가능 핸들러(mail_admins) 미사용.
#   - 웹서버(nginx) access log 익명화는 6단계에서 설정.
# * HTTPS 강제/보안 쿠키/HSTS 등은 production.py 에서 켠다.
