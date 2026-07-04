"""핵심 보안 로직 검증 테스트.

이 프로젝트에서 가장 중요한 규칙 두 가지를 자동으로 검증한다:
1) 익명 신고 시 신원 필드가 '서버에서 강제로' 비워지는가 (폼 + 모델 양쪽)
2) 실명 신고 시 이름/연락처가 필수로 검증되는가
"""
from django.test import TestCase

from .forms import ReportForm
from .models import Report


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
