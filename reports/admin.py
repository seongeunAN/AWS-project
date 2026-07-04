"""관리자 페이지 (4단계).

구현 목표:
1. 신원(이름·연락처) 열람은 'view_identity' 권한을 가진 관리자만 가능.
2. 상태(접수/검토중/처리완료)를 관리자가 변경 가능.
3. 신원을 '열람'하는 순간(신고 상세를 여는 시점) 감사 로그를 자동 기록.
4. 감사 로그는 admin에서 '읽기 전용'으로만 조회 가능(추가/수정/삭제 불가).

설계 근거:
- 신원 필드는 admin에서도 '읽기 전용'으로 노출한다. 관리자가 임의로 신원을
  수정/조작하지 못하게 하기 위함(무결성).
- 목록(list) 화면에는 신원 필드를 절대 넣지 않는다. 목록은 로그 없이 여러 건이
  한 번에 보이므로, 여기에 신원을 넣으면 '열람 기록 없는 노출'이 된다.
  신원은 개별 상세를 열 때만(=감사 로그가 남을 때만) 보이도록 한다.
"""
from django.contrib import admin

from .models import AccessAuditLog, Report

IDENTITY_FIELDS = ("reporter_name", "reporter_contact")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # 목록: 신원 필드는 절대 포함하지 않는다.
    list_display = ("id", "title", "status", "is_anonymous", "created_at")
    list_display_links = ("id", "title")
    list_filter = ("status", "is_anonymous", "created_at")
    list_editable = ("status",)  # 목록에서 상태를 바로 변경
    search_fields = ("title", "content")  # 신원 필드는 검색 대상에서 제외
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    def _can_view_identity(self, request):
        return request.user.has_perm("reports.view_identity")

    def get_fields(self, request, obj=None):
        """상세 편집 화면 필드 구성. 권한이 있을 때만 신원 필드를 노출한다."""
        common = ["title", "content", "is_anonymous", "status", "created_at", "updated_at"]
        if self._can_view_identity(request):
            # 신원 필드는 상태 위, 본문 아래에 배치
            return [
                "title",
                "content",
                "is_anonymous",
                *IDENTITY_FIELDS,
                "status",
                "created_at",
                "updated_at",
            ]
        return common

    def get_readonly_fields(self, request, obj=None):
        """상태만 편집 가능. 나머지(신원 포함)는 읽기 전용."""
        readonly = ["is_anonymous", "created_at", "updated_at"]
        if self._can_view_identity(request):
            readonly += list(IDENTITY_FIELDS)
        return readonly

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """신고 상세를 '열람'하는 시점에 감사 로그를 남긴다.

        - GET 요청(=화면을 여는 순간)에만 기록한다. (저장 POST 시 중복 기록 방지)
        - 신원 열람 권한이 있고, 해당 신고에 신원 정보가 실제로 있을 때만 기록한다.
        """
        if request.method == "GET" and self._can_view_identity(request):
            obj = self.get_object(request, object_id)
            if obj is not None and obj.has_identity:
                AccessAuditLog.objects.create(
                    report=obj,
                    admin_user=request.user,
                    action=AccessAuditLog.Action.VIEW_IDENTITY,
                )
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(AccessAuditLog)
class AccessAuditLogAdmin(admin.ModelAdmin):
    """신원 열람 감사 로그 — 읽기 전용."""

    list_display = ("viewed_at", "admin_user", "report", "action")
    list_filter = ("action", "admin_user", "viewed_at")
    readonly_fields = ("report", "admin_user", "action", "viewed_at")
    ordering = ("-viewed_at",)
    date_hierarchy = "viewed_at"

    # 감사 로그는 사람이 추가/수정/삭제할 수 없어야 한다 (변조 방지).
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
