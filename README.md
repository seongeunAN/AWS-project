# 도제학생 현장실습 부당대우 익명 신고 게시판

도제학교 학생이 현장실습 중 겪은 부당대우를 **로그인 없이** 신고할 수 있는 Django 웹 게시판입니다.
대상이 취약한 학생이고 내용이 민감하므로, **신고자 보호가 기능보다 우선**하도록 설계했습니다.

> **포지셔닝(정직한 범위)**
> 이 시스템은 "완전한 익명 보장"을 주장하지 않습니다. 실제로 보장하는 것은
> **신고자 식별 데이터의 최소화** — 즉 내부자 오남용·DB 유출·외부 자료제출 요구가 있어도
> 시스템이 내줄 신고자 IP가 존재하지 않는다는 점입니다.
> 통신사(ISP) 접속 기록이나 학교·회사 네트워크 관리자의 관찰은 막을 수 없습니다.
> 자세한 범위와 한계는 [docs/DEPLOY.md](docs/DEPLOY.md#-ip-미수집을-실제로-지키려면-범위와-한계) 참고.

---

## 핵심 설계 원칙

1. **익명이 기본값이고, 익명 선택 시 신원 필드는 서버가 강제로 비운다.**
   프론트에서 입력칸을 숨기는 것만으로는 조작이 가능하므로, 폼(`clean()`)과 모델(`save()`)
   **두 계층**에서 신원 값을 빈 문자열로 덮어씁니다.
2. **신고자 IP를 어디에도 저장하지 않는다.**
   DB에 IP 필드가 없고, 앱 코드가 `request.META`의 IP를 읽지 않으며,
   로깅 설정에서 요청 META를 외부로 보내는 `mail_admins` 핸들러를 제거했고,
   nginx access log 포맷에서도 `$remote_addr`를 뺐습니다.
3. **신원 정보는 일반 화면에 절대 렌더링하지 않는다.**
   목록/상세 뷰는 `.only()`로 신원 필드를 아예 조회조차 하지 않습니다.
4. **관리자 열람은 권한으로 통제하고, 감사 로그로 남기고, MFA로 보호한다.**
   관리자 계정 하나가 뚫리면 모든 실명이 노출되기 때문입니다.

---

## 기술 스택

| 구분 | 선택 |
|------|------|
| 언어 | Python 3.11+ |
| 프레임워크 | Django 5.1 |
| DB (로컬 / 배포) | SQLite / PostgreSQL (AWS RDS, 저장 암호화) |
| 앱 서버 / 웹 서버 | Gunicorn / Nginx |
| 관리자 MFA | django-otp (TOTP + 복구 코드) |
| 설정 관리 | django-environ (`.env`) |

---

## 빠른 시작 (로컬)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.local  # Windows: set DJANGO_SETTINGS_MODULE=...
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- 신고 게시판: <http://127.0.0.1:8000/>
- 관리자 페이지: <http://127.0.0.1:8000/admin/>

로컬 설정(`config/settings/local.py`)은 SQLite + `DEBUG=True`이며,
개발 편의를 위해 관리자 MFA를 강제하지 않습니다(`ADMIN_REQUIRE_OTP=False`).

### 테스트

```bash
python manage.py test
```

핵심 보안 규칙(익명 강제 비우기, 신원 비노출, 권한 통제, 감사 로그, IP 미수집)이
[reports/tests.py](reports/tests.py)에서 자동 검증됩니다.

---

## 화면 구성

| URL | 화면 | 비고 |
|-----|------|------|
| `/` | 신고 목록 | 제목·상태·접수시각만 노출 |
| `/new/` | 신고 작성 | 상단에 개인정보 고지문, 익명/실명 라디오 |
| `/<pk>/` | 신고 상세 | 제목·내용·상태만 노출 |
| `/admin/` | 관리자 | 신원 열람(권한 필요) + 상태 변경 + 감사 로그 |

---

## 데이터 모델

### `Report` — 신고 글

| 필드 | 설명 | 일반 화면 노출 |
|------|------|----------------|
| `title` / `content` | 제목 / 신고 내용 | O |
| `is_anonymous` | 익명 여부 (기본값 `True`) | O |
| `reporter_name` / `reporter_contact` | 신원: 이름 / 연락처 | **X** (권한 있는 관리자만) |
| `status` | `RECEIVED`(접수) / `REVIEWING`(검토중) / `DONE`(처리완료) | O |
| `created_at` / `updated_at` | 접수 / 수정 시각 | O |

**의도적으로 없는 필드: `ip_address`, `user_agent` 등 신고자 추적 정보.**

### `AccessAuditLog` — 신원 열람 감사 로그

`report`, `admin_user`, `action`(`VIEW_IDENTITY`), `viewed_at`.
"어떤 관리자가 언제 어떤 신고의 신원을 열람했는지"를 기록하며, 여기에도 신고자 IP는 남기지 않습니다.

---

## 관리자 페이지 동작

- **신원 열람 권한 분리**: Django admin 접근 권한과 별개로 `reports.view_identity`
  커스텀 권한을 가진 관리자만 이름·연락처를 볼 수 있습니다. 권한이 없으면 해당 필드가
  화면 구성에서 아예 빠집니다.
- **목록에는 신원을 넣지 않는다**: 목록은 여러 건이 한 번에 보여 "감사 로그 없는 노출"이
  되므로, 신원은 개별 상세를 열 때만 — 즉 열람 기록이 남을 때만 — 보입니다.
- **감사 로그 자동 기록**: 신원이 있는 신고의 상세 화면을 GET으로 여는 순간
  `AccessAuditLog`가 생성됩니다. (저장 POST에서는 중복 기록하지 않음)
- **감사 로그는 읽기 전용**: admin에서 추가/수정/삭제가 모두 막혀 있습니다(변조 방지).
- **신원 필드는 관리자도 읽기 전용**: 관리자가 편집할 수 있는 것은 `status`뿐입니다.

### 신원 열람 권한 부여 방법
`/admin/` → 사용자(User) → 해당 관리자 → *사용자 권한*에서
`reports | 신고 | 신원 정보(이름·연락처) 열람 가능` 추가.
(슈퍼유저는 모든 권한을 갖습니다.)

---

## 보안 설정

### 환경변수 (`.env`)
`SECRET_KEY`, DB 비밀번호 등은 코드에 하드코딩하지 않습니다.
[.env.example](.env.example)을 복사해 `.env`로 만들고 값을 채우세요. `.env`는 `.gitignore` 대상입니다.

```bash
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

배포 설정(`production.py`)은 `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, DB 접속 정보가
없으면 **기동 자체가 실패**하도록 되어 있습니다. 잘못된 기본값으로 배포되는 것을 막기 위함입니다.

### 배포 시 자동 적용되는 보안 설정
`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
HSTS(1년 + `includeSubDomains` + preload), `SECURE_CONTENT_TYPE_NOSNIFF`,
`X_FRAME_OPTIONS=DENY`, `SECURE_REFERRER_POLICY=same-origin`, RDS 연결 `sslmode=require`.

### 관리자 MFA
`ADMIN_REQUIRE_OTP=True`이면 `reports/apps.py`가 admin 사이트를 `OTPAdminSite`로 교체해
2단계 인증을 통과한 관리자만 접근할 수 있습니다. 배포에서는 기본 `True`입니다.

등록 절차: admin → *TOTP devices* → 관리자 본인 계정으로 기기 추가 → QR을 인증앱으로 스캔.
계정 잠김에 대비해 *Static devices*로 복구 코드도 함께 만들어 두세요.

---

## AWS 배포

EC2 1대 + RDS(PostgreSQL) 구성입니다.

```
사용자 ──HTTPS──> [ Nginx (EC2) ] ──소켓──> [ Gunicorn+Django (EC2) ] ──TLS──> [ RDS PostgreSQL ]
                    IP 미기록                    IP 미수집                     저장 암호화
```

전체 절차는 [docs/DEPLOY.md](docs/DEPLOY.md)에 초보자 기준으로 정리되어 있습니다.
설정 파일은 [deploy/](deploy/)에 있습니다: `nginx.conf`(IP 미기록 로그 포맷 + TLS 프록시),
`gunicorn.service`(systemd 유닛), `certbot-notes.md`(Let's Encrypt HTTPS).

> **배포자 필수 수칙**: VPC Flow Logs, ALB 액세스 로그, CloudFront/WAF 로깅을 켜면
> 앱 단의 IP 미수집 노력이 무력화됩니다. DEPLOY.md의 체크리스트를 반드시 확인하세요.

---

## 프로젝트 구조

```
AWS-project/
├── config/                  # Django 프로젝트 설정
│   ├── settings/
│   │   ├── base.py          # 공통 설정 + IP 미로깅 LOGGING
│   │   ├── local.py         # SQLite, DEBUG=True
│   │   └── production.py    # PostgreSQL, HTTPS 강제, MFA 강제
│   └── urls.py
├── reports/                 # 신고 게시판 앱
│   ├── models.py            # Report, AccessAuditLog
│   ├── forms.py             # 익명/실명 선택 + 서버측 강제 검증
│   ├── views.py             # 작성/목록/상세 (신원 미조회)
│   ├── admin.py             # 권한 기반 신원 열람 + 감사 로그
│   ├── tests.py             # 보안 규칙 자동 검증
│   └── templates/reports/
├── deploy/                  # nginx / gunicorn / certbot 설정
├── docs/
│   ├── PLAN.md              # 개발 계획 및 설계 근거
│   └── DEPLOY.md            # AWS 배포 가이드
├── .env.example
└── requirements.txt
```

---

## 운영 시 주의사항

- **`.env`를 커밋하지 마세요.** `SECRET_KEY`와 DB 비밀번호가 들어 있습니다.
- **신원 열람 권한은 최소 인원에게만** 부여하세요. 권한 = 전체 실명 접근입니다.
- **감사 로그를 주기적으로 확인**하세요. 열람 기록이 곧 내부자 오남용 억제 장치입니다.
- **nginx 설정 수정 시 `$remote_addr`를 다시 넣지 마세요.**
- 학생에게는 **"개인 기기·개인 네트워크에서 작성"**을 안내하세요. 학교·회사 망에서의
  접속은 그 망의 관리자(가해 주체일 수 있음)에게 보입니다.
