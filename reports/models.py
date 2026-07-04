"""신고 게시판 데이터 모델.

핵심 보안 원칙(모델 레벨):
- 신고자 IP를 저장하는 필드를 '의도적으로 두지 않습니다'. (ip_address, user_agent 등 없음)
- 익명 신고인 경우, 신원 필드(reporter_name/reporter_contact)를 저장 직전에
  '서버가 강제로' 비웁니다. 폼 검증에 더해 모델 save()에서도 한 번 더 방어합니다.
  (프론트 조작, 폼을 거치지 않는 저장 경로 등 어떤 경우에도 익명이면 신원이 남지 않도록)
"""
from django.conf import settings
from django.db import models


class Report(models.Model):
    """부당대우 신고 글."""

    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "접수"
        REVIEWING = "REVIEWING", "검토중"
        DONE = "DONE", "처리완료"

    # 일반 화면에 노출되는 신고 본문
    title = models.CharField("제목", max_length=200)
    content = models.TextField("내용")

    # 익명 여부 (기본값: 익명)
    is_anonymous = models.BooleanField("익명 신고", default=True)

    # 신원 정보 — 일반 화면에는 절대 노출하지 않고, 관리자만 admin에서 열람.
    # 익명 신고 시에는 서버가 강제로 빈 값으로 저장한다.
    reporter_name = models.CharField("신고자 이름", max_length=100, blank=True)
    reporter_contact = models.CharField("신고자 연락처", max_length=100, blank=True)

    # 처리 상태 (관리자가 변경 — 4단계)
    status = models.CharField(
        "처리 상태",
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )

    created_at = models.DateTimeField("접수 시각", auto_now_add=True)
    updated_at = models.DateTimeField("수정 시각", auto_now=True)

    # 주의: 신고자 IP/User-Agent를 저장하는 필드는 두지 않는다. (보안 요구사항)

    class Meta:
        verbose_name = "신고"
        verbose_name_plural = "신고 목록"
        ordering = ["-created_at"]
        permissions = [
            # 이 권한을 가진 관리자만 신원(이름·연락처)을 열람할 수 있다.
            # (Django admin 접근 권한과 별개로, 신원 열람을 한 번 더 통제)
            ("view_identity", "신원 정보(이름·연락처) 열람 가능"),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title}"

    def save(self, *args, **kwargs):
        # 익명이면 신원 필드를 강제로 비운다 (최종 방어선).
        if self.is_anonymous:
            self.reporter_name = ""
            self.reporter_contact = ""
        super().save(*args, **kwargs)

    @property
    def has_identity(self):
        """관리자가 열람할 신원 정보가 있는지 여부."""
        return bool(self.reporter_name or self.reporter_contact)


class AccessAuditLog(models.Model):
    """신원 정보 열람 감사 로그.

    '어떤 관리자가 언제 어떤 신고의 신원을 열람했는지' 기록한다.
    - 이 로그에도 신고자 IP는 저장하지 않는다.
    - 실제 기록(열람 시 자동 생성)은 4단계 admin에서 연결한다.
    """

    class Action(models.TextChoices):
        VIEW_IDENTITY = "VIEW_IDENTITY", "신원 정보 열람"

    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="access_logs",
        verbose_name="대상 신고",
    )
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="열람 관리자",
    )
    action = models.CharField(
        "행위",
        max_length=30,
        choices=Action.choices,
        default=Action.VIEW_IDENTITY,
    )
    viewed_at = models.DateTimeField("열람 시각", auto_now_add=True)

    class Meta:
        verbose_name = "신원 열람 로그"
        verbose_name_plural = "신원 열람 로그"
        ordering = ["-viewed_at"]

    def __str__(self):
        who = self.admin_user or "(알 수 없음)"
        return f"{who} - {self.get_action_display()} @ {self.viewed_at:%Y-%m-%d %H:%M}"
