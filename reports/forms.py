"""신고 작성 폼 + 서버측 검증.

이 폼이 익명성 보호의 핵심 지점입니다.
- 익명/실명은 라디오 버튼으로 선택합니다. 기본값은 '익명'.
- 익명 선택 시: 사용자가 이름/연락처를 보냈더라도 서버가 '강제로 비웁니다'.
  (프론트에서 필드를 숨기는 것만으로는 조작 가능하므로 서버에서 최종 처리)
- 실명 선택 시: 이름/연락처를 '필수'로 검증합니다.
"""
from django import forms

from .models import Report


class ReportForm(forms.ModelForm):
    # 익명/실명 라디오. 모델의 BooleanField(is_anonymous)를 라디오로 표현한다.
    # 값이 문자열 'True'/'False'로 들어오므로 coerce로 실제 bool로 변환한다.
    is_anonymous = forms.TypedChoiceField(
        label="신고 방식",
        choices=[
            (True, "익명으로 신고"),
            (False, "신원을 밝히고 신고 (후속 연락 가능)"),
        ],
        coerce=lambda v: v in (True, "True", "true", "1"),
        widget=forms.RadioSelect,
        initial=True,
        required=True,
    )

    class Meta:
        model = Report
        # status/created_at 등은 폼에서 받지 않는다. (관리자만 상태 변경)
        fields = ["title", "content", "is_anonymous", "reporter_name", "reporter_contact"]
        labels = {
            "title": "제목",
            "content": "신고 내용",
            "reporter_name": "이름",
            "reporter_contact": "연락처 (전화 또는 이메일)",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 신원 필드는 폼 레벨에서는 선택 입력.
        # 실명일 때만 clean()에서 필수로 검증한다.
        self.fields["reporter_name"].required = False
        self.fields["reporter_contact"].required = False

    def clean(self):
        cleaned = super().clean()
        is_anonymous = cleaned.get("is_anonymous")

        if is_anonymous:
            # 익명: 신원 필드를 서버에서 강제로 비운다.
            # (사용자가 값을 보냈더라도 무시하고 저장하지 않는다)
            cleaned["reporter_name"] = ""
            cleaned["reporter_contact"] = ""
        else:
            # 실명: 이름/연락처 필수.
            if not (cleaned.get("reporter_name") or "").strip():
                self.add_error("reporter_name", "실명 신고 시 이름을 입력해 주세요.")
            if not (cleaned.get("reporter_contact") or "").strip():
                self.add_error(
                    "reporter_contact", "실명 신고 시 연락처를 입력해 주세요."
                )
        return cleaned
