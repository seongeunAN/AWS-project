#!/usr/bin/env python
"""Django 관리 명령 진입점.

기본 설정은 로컬 개발용(config.settings.local)입니다.
배포 시에는 DJANGO_SETTINGS_MODULE 환경변수로 production을 지정합니다.
"""
import os
import sys


def main():
    # 환경변수로 지정하지 않으면 로컬(SQLite, DEBUG=True) 설정을 사용
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django를 불러오지 못했습니다. 가상환경을 활성화했는지, "
            "'pip install -r requirements.txt'를 실행했는지 확인하세요."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
