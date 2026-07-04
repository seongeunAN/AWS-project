"""사용자용 URL (작성 / 목록 / 상세)."""
from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.ReportListView.as_view(), name="list"),
    path("new/", views.ReportCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ReportDetailView.as_view(), name="detail"),
]
