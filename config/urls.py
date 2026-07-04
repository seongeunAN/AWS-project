"""프로젝트 URL 설정.

- /admin/  : 관리자 페이지
- /        : 사용자용 신고 게시판 (reports 앱)
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("reports.urls")),
]
