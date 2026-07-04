"""공통 Django 설정 (base).

로컬(local.py)과 배포(production.py)가 이 파일을 상속합니다.
- 여기에는 환경에 상관없이 공통인 값만 둡니다.
- SECRET_KEY, DEBUG, 데이터베이스, 보안 스위치 등 '환경마다 달라지는' 값은
  local.py / production.py 에서 정의합니다. (5단계에서 .env로 분리)
"""
from pathlib import Path

# 프로젝트 최상위 경로 (이 파일 기준 3단계 상위: config/settings/base.py -> AWS-project/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 로컬 앱
    "reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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

# --- 보안/개인정보 관련 주석 (실제 설정은 단계별로 추가) ---
# * 신고자 IP는 어디에도 저장하지 않습니다.
#   - 이 프로젝트에는 IP를 기록하는 커스텀 미들웨어가 없습니다. (5단계에서 재확인)
#   - Django는 기본적으로 요청 IP를 DB에 저장하지 않습니다.
# * 관리자 MFA(django-otp), HTTPS 강제 설정은 5단계에서 production.py에 추가합니다.
