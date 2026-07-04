"""핵심 보안 로직 검증 테스트.

이 프로젝트에서 가장 중요한 규칙 두 가지를 자동으로 검증한다:
1) 익명 신고 시 신원 필드가 '서버에서 강제로' 비워지는가 (폼 + 모델 양쪽)
2) 실명 신고 시 이름/연락처가 필수로 검증되는가
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import ReportForm
from .models import AccessAuditLog, Report


class AnonymousEnforcementFormTests(TestCase):
    def test_anonymous_clears_identity_even_if_submitted(self):
        """익명 선택 시, 사용자가 이름/연락처를 보내도 서버가 비워야 한다."""
        form = ReportForm(
            data={
                "title": "부당대우 신고",
                "content": "내용입니다.",
                "is_anonymous": "True",
                # 프론트 조작 등으로 신원이 함께 전송된 상황을 가정
                "reporter_name": "홍길동",
                "reporter_contact": "010-0000-0000",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["reporter_name"], "")
        self.assertEqual(form.cleaned_data["reporter_contact"], "")

        report = form.save()
        self.assertTrue(report.is_anonymous)
        self.assertEqual(report.reporter_name, "")
        self.assertEqual(report.reporter_contact, "")

    def test_named_requires_identity(self):
        """실명 선택 시 이름/연락처가 없으면 폼이 무효여야 한다."""
        form = ReportForm(
            data={
                "title": "실명 신고",
                "content": "내용입니다.",
                "is_anonymous": "False",
                "reporter_name": "",
                "reporter_contact": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("reporter_name", form.errors)
        self.assertIn("reporter_contact", form.errors)

    def test_named_saves_identity(self):
        """실명 선택 + 신원 입력 시 정상 저장되어야 한다."""
        form = ReportForm(
            data={
                "title": "실명 신고",
                "content": "내용입니다.",
                "is_anonymous": "False",
                "reporter_name": "홍길동",
                "reporter_contact": "hong@example.com",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        report = form.save()
        self.assertFalse(report.is_anonymous)
        self.assertEqual(report.reporter_name, "홍길동")
        self.assertEqual(report.reporter_contact, "hong@example.com")


class AnonymousEnforcementModelTests(TestCase):
    def test_model_save_clears_identity_when_anonymous(self):
        """폼을 거치지 않고 모델을 직접 저장해도, 익명이면 신원이 비워져야 한다."""
        report = Report.objects.create(
            title="직접 저장",
            content="내용",
            is_anonymous=True,
            reporter_name="홍길동",
            reporter_contact="010-1234-5678",
        )
        report.refresh_from_db()
        self.assertEqual(report.reporter_name, "")
        self.assertEqual(report.reporter_contact, "")

    def test_no_ip_field_on_model(self):
        """모델에 IP/UA 등 신고자 추적 필드가 존재하지 않아야 한다."""
        field_names = {f.name for f in Report._meta.get_fields()}
        for forbidden in ("ip_address", "ip", "user_agent", "remote_addr"):
            self.assertNotIn(forbidden, field_names)


class PublicScreenIdentityHidingTests(TestCase):
    """일반 화면(목록/상세)에 신원 정보가 절대 노출되지 않는지 검증."""

    def setUp(self):
        # 실명 신고를 하나 만들어 둔다 (신원 값이 DB에 실제로 존재하는 상황).
        self.named = Report.objects.create(
            title="실명 신고 제목",
            content="실명 신고 내용",
            is_anonymous=False,
            reporter_name="김실명",
            reporter_contact="secret-contact@example.com",
        )

    def test_list_does_not_leak_identity(self):
        resp = self.client.get(reverse("reports:list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "실명 신고 제목")
        self.assertNotContains(resp, "김실명")
        self.assertNotContains(resp, "secret-contact@example.com")

    def test_detail_does_not_leak_identity(self):
        resp = self.client.get(reverse("reports:detail", args=[self.named.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "실명 신고 내용")
        self.assertNotContains(resp, "김실명")
        self.assertNotContains(resp, "secret-contact@example.com")

    def test_create_via_post_named(self):
        """POST로 실명 신고 작성 → 상세로 리다이렉트, 화면엔 신원 비노출."""
        resp = self.client.post(
            reverse("reports:create"),
            data={
                "title": "새 실명 신고",
                "content": "내용",
                "is_anonymous": "False",
                "reporter_name": "박실명",
                "reporter_contact": "010-1111-2222",
            },
        )
        self.assertEqual(resp.status_code, 302)
        report = Report.objects.get(title="새 실명 신고")
        self.assertEqual(report.reporter_name, "박실명")
        # 리다이렉트된 상세 페이지에서도 신원은 안 보여야 한다.
        detail = self.client.get(resp.url)
        self.assertNotContains(detail, "박실명")
        self.assertNotContains(detail, "010-1111-2222")

    def test_create_via_post_anonymous_clears_identity(self):
        """POST로 익명 신고 시 신원이 함께 와도 저장되지 않아야 한다."""
        self.client.post(
            reverse("reports:create"),
            data={
                "title": "익명 신고 POST",
                "content": "내용",
                "is_anonymous": "True",
                "reporter_name": "무시될이름",
                "reporter_contact": "무시될연락처",
            },
        )
        report = Report.objects.get(title="익명 신고 POST")
        self.assertEqual(report.reporter_name, "")
        self.assertEqual(report.reporter_contact, "")


class AdminIdentityAuditTests(TestCase):
    """관리자 신원 열람 통제 + 감사 로그 자동 기록 검증."""

    def setUp(self):
        User = get_user_model()
        # 슈퍼유저는 모든 권한을 가지므로 view_identity 권한도 갖는다.
        self.admin = User.objects.create_superuser(
            username="admin", email="a@example.com", password="pw-strong-12345"
        )
        self.client.force_login(self.admin)

        self.named = Report.objects.create(
            title="실명 신고", content="내용", is_anonymous=False,
            reporter_name="김실명", reporter_contact="hong@example.com",
        )
        self.anon = Report.objects.create(
            title="익명 신고", content="내용", is_anonymous=True,
        )

    def test_view_named_report_creates_audit_log(self):
        """신원 있는 신고 상세를 열면 감사 로그가 생성된다."""
        url = reverse("admin:reports_report_change", args=[self.named.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # 상세 화면에는 관리자에게 신원이 보인다.
        self.assertContains(resp, "김실명")
        log = AccessAuditLog.objects.filter(report=self.named)
        self.assertEqual(log.count(), 1)
        self.assertEqual(log.first().admin_user, self.admin)
        self.assertEqual(log.first().action, AccessAuditLog.Action.VIEW_IDENTITY)

    def test_view_anonymous_report_creates_no_log(self):
        """신원이 없는(익명) 신고를 열면 감사 로그가 생기지 않는다."""
        url = reverse("admin:reports_report_change", args=[self.anon.pk])
        self.client.get(url)
        self.assertEqual(AccessAuditLog.objects.count(), 0)

    def test_status_can_be_changed(self):
        """관리자가 상태를 변경할 수 있다."""
        url = reverse("admin:reports_report_change", args=[self.anon.pk])
        self.client.post(url, data={
            "title": self.anon.title,
            "content": self.anon.content,
            "status": Report.Status.DONE,
            "_save": "저장",
        })
        self.anon.refresh_from_db()
        self.assertEqual(self.anon.status, Report.Status.DONE)

    def test_audit_log_is_read_only(self):
        """감사 로그는 추가/수정/삭제가 불가능해야 한다."""
        from .admin import AccessAuditLogAdmin
        from django.contrib.admin.sites import site
        ma = AccessAuditLogAdmin(AccessAuditLog, site)

        class _Req:
            user = self.admin
        req = _Req()
        self.assertFalse(ma.has_add_permission(req))
        self.assertFalse(ma.has_change_permission(req))
        self.assertFalse(ma.has_delete_permission(req))


class AdminIdentityPermissionTests(TestCase):
    """view_identity 권한이 없는 staff는 신원을 열람할 수 없다."""

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff", password="pw-strong-12345", is_staff=True,
        )
        # Report 열람/변경 권한은 주되, view_identity 권한은 주지 않는다.
        from django.contrib.auth.models import Permission
        for codename in ("view_report", "change_report"):
            self.staff.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(self.staff)

        self.named = Report.objects.create(
            title="실명 신고", content="내용", is_anonymous=False,
            reporter_name="비밀이름", reporter_contact="secret@example.com",
        )

    def test_staff_without_permission_cannot_see_identity(self):
        url = reverse("admin:reports_report_change", args=[self.named.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "비밀이름")
        self.assertNotContains(resp, "secret@example.com")
        # 열람하지 못했으므로 감사 로그도 남지 않는다.
        self.assertEqual(AccessAuditLog.objects.count(), 0)
