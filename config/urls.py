"""프로젝트 URL 설정.

2단계에서는 관리자(admin)만 연결합니다.
사용자용 화면(작성/목록/상세)은 3단계에서 reports.urls 로 추가합니다.
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # 3단계에서 추가 예정:
    # path("", include("reports.urls")),
]
