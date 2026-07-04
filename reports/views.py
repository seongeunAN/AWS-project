"""사용자용 화면 뷰 (작성 / 목록 / 상세).

보안 원칙(뷰·템플릿 레벨):
- 이 화면들은 '일반 사용자'가 보는 곳이다. 신원 정보(reporter_name/reporter_contact)는
  절대 전달·렌더링하지 않는다.
- 목록/상세는 신원 필드를 아예 조회하지 않도록 .only()/.defer()로 방어한다.
  (실수로 템플릿에 넣더라도 값이 넘어가지 않게)
- 신고자 IP를 확인하거나 기록하는 코드는 두지 않는다. (request.META 접근 금지)
"""
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import ReportForm
from .models import Report

# 일반 화면에서 다루는 '안전한' 필드 목록. 신원 필드는 여기에 포함하지 않는다.
PUBLIC_FIELDS = ["id", "title", "content", "status", "created_at"]


class ReportListView(ListView):
    """신고 목록. 신원 필드는 조회하지 않는다."""

    model = Report
    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 20

    def get_queryset(self):
        # .only()로 신원 필드를 아예 로드하지 않는다 (실수 노출 방지).
        return Report.objects.only(*PUBLIC_FIELDS)


class ReportDetailView(DetailView):
    """신고 상세. 신원 필드는 조회하지 않는다."""

    model = Report
    template_name = "reports/report_detail.html"
    context_object_name = "report"

    def get_queryset(self):
        return Report.objects.only(*PUBLIC_FIELDS)


class ReportCreateView(CreateView):
    """신고 작성. 로그인 없이 누구나 작성 가능."""

    model = Report
    form_class = ReportForm
    template_name = "reports/report_form.html"

    def get_success_url(self):
        return reverse_lazy("reports:detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "신고가 정상적으로 접수되었습니다.")
        return response
