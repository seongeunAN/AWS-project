"""관리자 페이지 등록 (2단계: 최소 등록).

여기서는 마이그레이션/동작 확인을 위해 모델만 기본 등록합니다.
- 신원 필드의 열람 통제, 상태 변경, 열람 시 감사 로그 자동 기록 등
  '본격적인 관리자 기능'은 4단계에서 이 파일을 확장하며 구현합니다.
"""
from django.contrib import admin

from .models import AccessAuditLog, Report

admin.site.register(Report)
admin.site.register(AccessAuditLog)
