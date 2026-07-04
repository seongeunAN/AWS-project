# HTTPS 설정 (Let's Encrypt / certbot)

무료 인증서로 HTTPS를 켜는 방법입니다. 도메인이 EC2 서버 IP를 가리키도록
DNS(A 레코드)가 먼저 설정되어 있어야 합니다.

## 1. certbot 설치 (Ubuntu 기준)

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

- `certbot`: 인증서를 발급/자동 갱신해 주는 도구
- `python3-certbot-nginx`: nginx 설정을 자동으로 잡아주는 플러그인

## 2. 인증서 발급

먼저 `deploy/nginx.conf`를 서버에 배치하고 nginx가 80포트로 떠 있어야 합니다.

```bash
sudo certbot --nginx -d report.school.example.com
```

- `-d` 뒤에 실제 도메인을 넣습니다.
- 이메일 입력, 약관 동의를 거치면 인증서가 발급되고
  nginx 설정에 인증서 경로가 자동으로 연결됩니다.

## 3. 자동 갱신 확인

Let's Encrypt 인증서는 90일마다 만료되므로 자동 갱신이 중요합니다.

```bash
sudo certbot renew --dry-run   # 갱신이 정상 동작하는지 테스트
```

- certbot 설치 시 갱신 타이머(systemd timer)가 자동 등록됩니다.
- `systemctl list-timers | grep certbot` 로 확인 가능.

## 4. (대안) AWS ACM + 로드밸런서

EC2 앞에 ALB(Application Load Balancer)를 두는 구성이라면,
certbot 대신 **AWS Certificate Manager(ACM)** 에서 무료 인증서를 발급받아
ALB에 붙이는 방식도 가능합니다. 단일 EC2 + nginx 구성에서는 위의 certbot이 간단합니다.

---
참고: HTTPS가 켜지면 Django의 `SECURE_SSL_REDIRECT`(production.py)가
http 접속을 https로 되돌리고, nginx가 `X-Forwarded-Proto`를 넘겨
Django가 "이미 https"임을 인식합니다. (무한 리다이렉트 방지)
