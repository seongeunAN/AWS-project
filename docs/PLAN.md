# 도제학생 현장실습 부당대우 익명 신고 게시판 — 개발 계획 (1단계)

> 이 문서는 **1단계: 계획 수립** 산출물입니다. 아직 코드는 없습니다.
> 프로젝트 구조, 데이터 모델, 단계별 할 일을 먼저 확정한 뒤 2단계부터 코드를 작성합니다.

---

## 1. 프로젝트 개요

도제학교 학생이 현장실습 중 겪은 부당대우를 **로그인 없이** 안전하게 신고하는 웹 게시판입니다.
대상이 취약한 학생이고 내용이 민감하므로, **신고자의 익명성 보호가 기능보다 우선**합니다.

핵심 설계 원칙(모든 결정의 기준):
1. **익명이 기본값**이고, 익명 선택 시 신원 필드는 **서버에서 강제로 비워** 저장한다. (프론트 숨김만으로는 불충분)
2. **신고자 IP를 어디에도 저장하지 않는다.** (DB, 앱 로그, 웹서버 access log 모두)
3. **신원 정보(이름·연락처)는 일반 화면에 절대 렌더링하지 않는다.** 오직 인증된 관리자만 admin에서 열람한다.
4. **관리자 열람은 감사 로그로 남기고, 관리자 로그인은 MFA로 보호**한다. 관리자 계정 하나가 뚫리면 모든 실명이 노출되기 때문이다.

---

## 2. 기술 스택

| 구분 | 선택 | 이유 |
|------|------|------|
| 언어 | Python 3.11+ | 요구사항 |
| 웹 프레임워크 | Django 5.x | 관리자 페이지 내장 + RBAC(권한) 기본 제공. 실명 열람 통제에 유리 |
| DB (로컬) | SQLite | 초기 개발용, 설치 불필요 |
| DB (배포) | PostgreSQL (AWS RDS) | 요구사항, 저장 암호화 지원 |
| 앱 서버 | Gunicorn | 표준 WSGI 서버 |
| 웹 서버 | Nginx | 리버스 프록시 + TLS 종단 + access log IP 익명화 |
| MFA | django-otp + qrcode | admin 2단계 인증 |
| 필드 암호화 | (검토) 애플리케이션 레벨 대칭 암호화 | 신원 필드 추가 보호 — 5단계에서 도입 여부 결정 |
| 설정 관리 | django-environ (.env) | SECRET_KEY/DB 비밀번호 등 하드코딩 금지 |

---

## 3. 파일 트리 (최종 목표 형태)

```
AWS-project/
├── docs/
│   ├── PLAN.md                      # (1단계) 이 문서
│   └── DEPLOY.md                    # (6단계) AWS 배포 가이드
├── .env.example                     # (5단계) 환경변수 템플릿 (실제 .env는 git 제외)
├── .gitignore
├── requirements.txt
├── manage.py
├── config/                          # Django 프로젝트 설정 패키지
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                  # 공통 설정
│   │   ├── local.py                 # 로컬(SQLite, DEBUG=True)
│   │   └── production.py            # 배포(PostgreSQL, 보안 강제)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── reports/                         # 신고 게시판 앱
│   ├── __init__.py
│   ├── models.py                    # Report, AccessAuditLog
│   ├── forms.py                     # 익명/실명 선택 + 서버측 검증
│   ├── views.py                     # 작성/목록/상세 (신원 비노출)
│   ├── admin.py                     # 실명 열람 + 상태 변경 + 감사 로그 기록
│   ├── urls.py
│   ├── apps.py
│   ├── migrations/
│   └── templates/reports/
│       ├── base.html
│       ├── report_form.html         # 개인정보 고지문 포함
│       ├── report_list.html
│       └── report_detail.html
├── deploy/                          # (6단계) 배포 설정 파일
│   ├── nginx.conf                   # IP 익명화 / access log 비활성화
│   ├── gunicorn.service             # systemd 유닛
│   └── certbot-notes.md             # HTTPS(Let's Encrypt) 안내
└── README.md
```

---

## 4. 데이터 모델

### 4.1 `Report` (신고 글)

| 필드 | 타입 | 설명 | 비고 |
|------|------|------|------|
| `id` | AutoField (PK) | 기본키 | |
| `title` | CharField(200) | 제목 | 일반 화면 노출 O |
| `content` | TextField | 신고 내용 | 일반 화면 노출 O |
| `is_anonymous` | BooleanField | 익명 여부 | 기본값 `True` |
| `reporter_name` | CharField(100), blank | 신원: 이름 | **일반 화면 노출 X**, admin만 |
| `reporter_contact` | CharField(100), blank | 신원: 연락처 | **일반 화면 노출 X**, admin만 |
| `status` | CharField(choices) | 처리 상태 | `RECEIVED`/`REVIEWING`/`DONE` |
| `created_at` | DateTimeField(auto_now_add) | 접수 시각 | |
| `updated_at` | DateTimeField(auto_now) | 수정 시각 | |

**의도적으로 없는 필드: `ip_address`, `user_agent` 등 신고자 추적 가능 정보.**
→ IP는 요청 처리 중에도 DB에 넣지 않는다. (보안 요구사항 6)

상태 값:
- `RECEIVED` 접수
- `REVIEWING` 검토중
- `DONE` 처리완료

서버측 검증 규칙(핵심):
- `is_anonymous == True` → `reporter_name`, `reporter_contact`를 **강제로 빈 문자열로 덮어써서 저장**. (사용자가 프론트를 조작해 값을 보내도 무시)
- `is_anonymous == False` → 이름/연락처 **필수 입력** 검증.

### 4.2 `AccessAuditLog` (신원 열람 감사 로그)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | AutoField (PK) | 기본키 |
| `report` | ForeignKey(Report, on_delete=SET_NULL, null) | 열람 대상 신고 |
| `admin_user` | ForeignKey(User, on_delete=SET_NULL, null) | 열람한 관리자 |
| `viewed_at` | DateTimeField(auto_now_add) | 열람 시각 |
| `action` | CharField | 예: `VIEW_IDENTITY` |

→ "어떤 관리자가 언제 어떤 신고의 신원을 열람했는지" 기록 (보안 요구사항: 감사 로그).
→ 이 로그 자체에도 신고자 IP는 넣지 않는다.

---

## 5. 단계별 할 일 요약

각 단계가 끝나면 **멈추고** 확인을 받은 뒤 다음 단계로 진행합니다.

### ✅ 1단계 — 계획 (현재)
- [x] 파일 트리, 데이터 모델, 단계 계획 문서화 (이 문서)
- 코드 없음. 확인 후 2단계로.

### 2단계 — Django 뼈대 + 모델/폼/검증
- `django-admin startproject` 로 `config` 프로젝트, `reports` 앱 생성
- `settings` 분리(base/local), SQLite 로컬 구동
- `Report`, `AccessAuditLog` 모델 작성 + 마이그레이션
- `ReportForm`: 익명/실명 라디오 + **서버측 강제 비우기/필수검증** 로직
- 산출물: `python manage.py runserver`로 뜨는 뼈대, admin 로그인 확인

### 3단계 — 사용자 화면
- 신고 작성 폼(상단 **개인정보 고지문** 포함)
- 목록 페이지 / 상세 페이지
- 상세·목록에서 `reporter_name`/`reporter_contact` **절대 렌더링하지 않음** (템플릿에서 원천 제외)
- 산출물: 로그인 없이 신고 작성 → 목록/상세 열람 흐름

### 4단계 — 관리자 페이지
- `ReportAdmin`: 신원 필드 열람(권한 있는 관리자만), `status` 인라인 변경
- 신원 필드 열람 시 `AccessAuditLog` 자동 기록
- `AccessAuditLogAdmin`: 읽기 전용 조회
- 산출물: admin에서 실명 열람 + 상태 변경 + 감사 로그 확인

### 5단계 — 보안 설정
- **IP 로그 차단**: 앱/미들웨어에서 IP 미수집. 요청 IP를 어디에도 기록하지 않음 확인
- **MFA**: `django-otp`로 admin 2단계 인증
- **HTTPS 관련 Django 설정**: `production.py`에 `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*` 등
- **.env 구성**: `SECRET_KEY`, DB 비밀번호 등 환경변수화 + `.env.example`
- (검토) 신원 필드 애플리케이션 레벨 암호화 도입 여부 결정
- 산출물: 보안 체크리스트 통과

### 6단계 — AWS 배포 가이드
- `docs/DEPLOY.md`: EC2 1대 + RDS(PostgreSQL) 구성, **RDS 저장 암호화 활성화** 안내
- `deploy/nginx.conf`: **access log IP 익명화 또는 비활성화** + TLS 프록시
- `deploy/gunicorn.service`: systemd 유닛
- HTTPS(certbot 또는 ACM) 적용 안내
- 산출물: 따라 하면 배포되는 가이드 + 설정 파일

---

## 6. 보안·개인정보 결정 요약 (왜 이렇게 하는가)

| 결정 | 이유 |
|------|------|
| 익명이 기본값 + 서버측 강제 비우기 | 학생이 실수로/조작으로 신원이 노출되는 것을 서버가 최종 방어 |
| IP 미저장 (DB·앱로그·nginx) | IP는 개인 식별 가능 정보. 신고자 역추적 위험 원천 차단 |
| 신원 필드 일반 화면 완전 제외 | 템플릿 단에서 아예 다루지 않아 실수 노출 가능성 제거 |
| admin MFA | 관리자 1명 계정 탈취 = 전체 실명 유출. 2차 방어선 필수 |
| 감사 로그 | 열람 책임 추적. 내부자 오남용 억제 |
| HTTPS 강제 | 전송 구간 도청 방지 |
| RDS 암호화 + 필드 암호화 검토 | 저장 데이터 유출 시 피해 최소화 |
| 개인정보 고지문 | 실명 선택의 의미(관리자 열람 가능)를 사전 고지 |
| .env 비밀정보 관리 | 코드/깃에 비밀 노출 방지 |

---

## 7. 다음 행동

이 계획(파일 트리·데이터 모델·단계)이 괜찮으면 알려주세요.
확인해 주시면 **2단계(Django 뼈대 + 모델/폼/검증)** 로 넘어가겠습니다.

수정하고 싶은 부분(예: 상태 값 이름, 신원 필드 종류, 암호화 범위 등)이 있으면 지금 말씀해 주세요.
