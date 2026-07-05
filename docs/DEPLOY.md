# AWS 배포 가이드 (EC2 1대 + RDS PostgreSQL)

도제학생 익명 신고 게시판을 AWS에 올리는 방법입니다. **초보자 기준**으로,
AWS 콘솔에서 직접 해야 하는 일과 서버에서 실행할 명령을 순서대로 적었습니다.

> **"AWS 부분은 내가 직접 해야 하나요?"** → 네. EC2/RDS 생성, 암호화 켜기,
> 방화벽(보안 그룹) 설정은 **당신이 AWS 콘솔에서** 직접 합니다.
> 이 저장소가 제공하는 것은 (1) 이 가이드와 (2) 서버에 올릴 설정 파일
> (`deploy/nginx.conf`, `deploy/gunicorn.service`, `deploy/certbot-notes.md`)입니다.

전체 그림:
```
사용자 ──HTTPS──> [ Nginx (EC2) ] ──소켓──> [ Gunicorn+Django (EC2) ] ──TLS──> [ RDS PostgreSQL ]
                    IP 미기록                    IP 미수집                     저장 암호화
```

---

## 0. 미리 준비할 것
- AWS 계정
- 도메인 1개 (예: `report.school.example.com`) — HTTPS에 필요
- SSH 키페어 (EC2 접속용)

---

## 1. RDS (PostgreSQL) 만들기 — **콘솔에서**

1. AWS 콘솔 → **RDS** → **Create database**
2. **Standard create** → 엔진 **PostgreSQL**
3. Templates: **Free tier**(단일 학교 규모면 충분) 또는 Dev/Test
4. Settings:
   - DB instance identifier: `report-db`
   - Master username: `reportuser`
   - Master password: 강한 비밀번호 (나중에 `.env`의 `DB_PASSWORD`에 사용)
5. **⭐ Storage → Encryption → "Enable encryption" 체크** (RDS 저장 암호화)
   - 이게 요구사항입니다. 신원 데이터가 디스크에 암호화되어 저장됩니다.
   - KMS 키는 기본(aws/rds)으로 두어도 됩니다.
6. Connectivity:
   - **Public access: No** (인터넷에서 DB로 직접 접속 차단 — EC2를 통해서만 접근)
   - VPC 보안 그룹: 새로 만들거나 기존 선택 (2-3단계에서 EC2만 허용하도록 조정)
7. Additional configuration → Initial database name: `reportdb`
8. **Create database** 클릭 → 생성되면 **엔드포인트(Endpoint)** 주소를 복사해 둡니다.
   (예: `report-db.xxxx.ap-northeast-2.rds.amazonaws.com` → `.env`의 `DB_HOST`)

---

## 2. EC2 (서버) 만들기 — **콘솔에서**

1. 콘솔 → **EC2** → **Launch instance**
2. Name: `report-web`
3. AMI: **Ubuntu Server 22.04 LTS**
4. Instance type: **t3.micro** (단일 학교 규모면 충분, 프리티어 대상)
5. Key pair: 기존 키 선택 또는 새로 생성 (`.pem` 파일 잘 보관)
6. Network settings → 보안 그룹(방화벽) 인바운드 규칙:
   - **SSH (22)**: 내 IP 만 허용 (My IP)
   - **HTTP (80)**: Anywhere (certbot 인증 + https 리다이렉트용)
   - **HTTPS (443)**: Anywhere
7. **Launch instance** → 생성되면 **퍼블릭 IP** 확인.

### RDS 보안 그룹 조정 (EC2만 DB 접근 허용)
- RDS의 보안 그룹 인바운드에 **PostgreSQL(5432)** 규칙 추가 →
  Source를 **EC2의 보안 그룹**으로 지정. (EC2에서만 DB 접속 가능해짐)

### 도메인 연결
- 도메인 DNS에서 **A 레코드**를 EC2 퍼블릭 IP로 설정.

---

## 3. 서버에 코드 배포 — **EC2에 SSH 접속 후**

```bash
# (내 PC에서) EC2 접속
ssh -i my-key.pem ubuntu@<EC2-퍼블릭-IP>

# (EC2 안에서) 필수 패키지
sudo apt update
sudo apt install -y python3-venv python3-pip nginx git

# 코드 받기
cd /home/ubuntu
git clone <이 저장소 URL> AWS-project
cd AWS-project

# 가상환경 + 의존성
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 환경변수(.env) 만들기
```bash
cp .env.example .env
nano .env     # 아래 값들을 실제 값으로 채운다
```
- `DJANGO_SECRET_KEY`: 아래 명령으로 생성한 값
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=report.school.example.com`
- `ADMIN_REQUIRE_OTP=True`  (관리자 MFA 강제)
- `DB_NAME=reportdb`, `DB_USER=reportuser`, `DB_PASSWORD=...`
- `DB_HOST=<RDS 엔드포인트>`, `DB_PORT=5432`, `DB_SSLMODE=require`
- `CSRF_TRUSTED_ORIGINS=https://report.school.example.com`

### DB 준비 & 정적 파일 수집
```bash
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate            # RDS에 테이블 생성
python manage.py collectstatic --noinput   # 정적 파일 모으기 (nginx가 서빙)
python manage.py createsuperuser    # 관리자 계정 생성
```

---

## 4. Gunicorn (앱 서버) 등록 — **EC2에서**

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/gunicorn.service
# (경로/사용자명이 다르면 파일을 열어 수정)
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
sudo systemctl status gunicorn      # active(running) 확인
```

---

## 5. Nginx (웹 서버) 설정 — **EC2에서**

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/report
# 파일 안의 server_name / 경로를 실제 도메인·경로로 수정
sudo ln -s /etc/nginx/sites-available/report /etc/nginx/sites-enabled/report
sudo rm -f /etc/nginx/sites-enabled/default   # 기본 사이트 제거
sudo nginx -t                        # 설정 문법 검사
sudo systemctl restart nginx
```

> 이 nginx 설정은 **신고자 IP를 access log에 남기지 않고**(익명 log_format),
> 실제 IP를 앱으로도 전달하지 않습니다. (X-Forwarded-For 비움)

---

## 6. HTTPS 켜기 — **EC2에서**

`deploy/certbot-notes.md` 참고. 요약:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d report.school.example.com
sudo certbot renew --dry-run         # 자동 갱신 테스트
```
HTTPS가 켜지면 `production.py`의 `SECURE_SSL_REDIRECT`가 http→https로 강제합니다.

---

## 7. 배포 후 점검 체크리스트

- [ ] `https://도메인/` 접속 시 자물쇠(HTTPS) 표시, 목록 페이지가 뜬다
- [ ] `http://도메인/` 접속 시 자동으로 https로 넘어간다
- [ ] `/new/`에서 익명 신고 → 목록/상세에 이름·연락처가 안 보인다
- [ ] `/admin/` 로그인 시 **2단계 인증(OTP)** 을 요구한다
- [ ] admin에서 실명 신고 상세를 열면 → "신원 열람 로그"에 기록이 남는다
- [ ] `sudo cat /var/log/nginx/report.access.log` 에 **IP가 없다**
- [ ] RDS 콘솔에서 **Encryption: Enabled** 로 표시된다
- [ ] `.env` 파일이 git에 커밋되지 않았다 (`.gitignore` 확인)

---

## ⭐ IP 미수집을 실제로 지키려면 (범위와 한계)

이 프로젝트의 IP 미수집은 **"우리 시스템(앱·nginx·DB)이 신고자 IP를 저장하지 않는다"**
는 뜻입니다. **네트워크 레벨의 익명성을 보장하지는 않습니다.** 정직하게 구분하세요.

**우리가 지키는 것 (데이터 최소화 / 심층 방어)**
- 내부자·DB 유출·자료제출 요구가 있어도, 시스템에 신고자 IP가 없으므로 내줄 것이 없다.
- 이것이 이 게시판의 실제 가치입니다. "익명 보장"이 아니라 "신고자 식별 데이터 최소화".

**배포자가 반드시 지킬 운영 수칙** — 아래를 켜면 위 노력이 무력화됩니다:
- [ ] **VPC Flow Logs**: 켜지 마세요. (서브넷/ENI 단위로 소스 IP가 기록됨)
- [ ] **ALB(로드밸런서) 액세스 로그**: ALB를 쓴다면 S3 액세스 로그에 클라이언트 IP가 남습니다.
      단일 EC2+nginx 구성을 쓰면 ALB 자체가 없어 이 문제를 피할 수 있습니다.
- [ ] **CloudFront / WAF 로깅**: 사용 시 IP가 로그로 쌓이므로 끄거나 사용하지 않기.
- [ ] **nginx access log**: 이미 `deploy/nginx.conf`에서 IP를 안 남기도록 했지만,
      수정 시 `$remote_addr`를 다시 넣지 않도록 주의.

**우리가 못 막는 것 (한계 — 학생에게 정직하게 고지)**
- 신고자의 **통신사(ISP)** 접속 기록.
- 신고자가 **회사·학교 네트워크로 접속하면** 그 네트워크 관리자(=가해 주체일 수 있음)가
  접속을 봅니다. → 신고 폼 상단에 "개인 기기·개인망에서 작성" 안내를 넣은 이유입니다.

> 포지셔닝 권고: 이 시스템을 "익명 보장"으로 홍보하지 마세요.
> **"내부자·자료제출·DB유출로부터 신고자를 보호한다"** 가 정직하고 방어 가능한 주장입니다.

## 운영 팁
- 코드 업데이트 시:
  ```bash
  cd /home/ubuntu/AWS-project && git pull
  source .venv/bin/activate && pip install -r requirements.txt
  export DJANGO_SETTINGS_MODULE=config.settings.production
  python manage.py migrate && python manage.py collectstatic --noinput
  sudo systemctl restart gunicorn
  ```
- 로그 확인: `sudo journalctl -u gunicorn -e` (앱 오류), `sudo tail /var/log/nginx/report.error.log`

## (심화) 신원 필드 애플리케이션 레벨 암호화
RDS 저장 암호화에 더해, 이름·연락처를 **DB에 저장하기 전 앱에서 한 번 더 암호화**하면
DB 덤프가 유출되어도 신원이 보호됩니다. `django-cryptography` 등을 이용해
`reporter_name`/`reporter_contact`를 암호화 필드로 바꾸는 방식이며,
키는 `.env`로 관리합니다. 필요 시 별도 단계로 도입할 수 있습니다.
