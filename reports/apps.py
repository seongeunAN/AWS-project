from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
    verbose_name = "신고 게시판"

    def ready(self):
        # ADMIN_REQUIRE_OTP=True 이면 관리자 페이지 로그인에 OTP(2단계 인증)를 강제한다.
        # OTPAdminSite 는 OTP 검증을 통과한(=인증앱으로 확인된) 관리자만 admin에
        # 접근하게 한다. 로컬(기본 False)에서는 적용하지 않아 개발이 편하다.
        from django.conf import settings

        if getattr(settings, "ADMIN_REQUIRE_OTP", False):
            from django.contrib import admin
            from django_otp.admin import OTPAdminSite

            # 기존에 등록된 ModelAdmin은 그대로 두고, 기본 admin.site의 로그인
            # 동작만 OTP 필수로 교체한다.
            admin.site.__class__ = OTPAdminSite
