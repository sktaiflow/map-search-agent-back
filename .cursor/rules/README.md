# Cursor Rules - map-search-agent-back

이 프로젝트는 **map-search-agent-back**를 위한 Cursor 에디터 규칙 모음입니다.

## 📁 규칙 구조

```
.cursor/rules/
├── core/                    # 핵심 규칙
│   ├── project-structure.mdc    # 프로젝트 구조 및 파일 조직
│   └── code-style.mdc          # 코드 스타일 및 포맷팅
├── python/                  # Python 기술 규칙
│   ├── python-best-practices.mdc  # Python 모범 사례
│   └── dependencies.mdc          # 의존성 관리
├── backend/                 # 백엔드 기술 규칙
│   ├── api-design.mdc           # API 설계 및 구현
│   └── database.mdc             # 데이터베이스 설계
├── quality/                 # 품질 관리 규칙
│   ├── testing.mdc              # 테스트 코드 작성
│   └── security.mdc             # 보안 규칙
└── deployment/              # 배포 및 인프라 규칙
    └── ci-cd.mdc               # CI/CD 파이프라인
```

## 🎯 규칙 카테고리

### Core (핵심 규칙)
- **project-structure.mdc**: 프로젝트 구조, 폴더 조직, 파일 명명 규칙
- **code-style.mdc**: 코드 스타일, 포맷팅, 주석 작성 규칙

### Python (Python 기술)
- **python-best-practices.mdc**: 타입 힌팅, 에러 처리, 디자인 패턴
- **dependencies.mdc**: 패키지 관리, 가상환경, 버전 관리

### Backend (백엔드 기술)
- **api-design.mdc**: RESTful API 설계, 응답 형식, 에러 처리
- **database.mdc**: 데이터베이스 모델, 쿼리 최적화, 마이그레이션

### Quality (품질 관리)
- **testing.mdc**: 테스트 구조, 픽스처, 커버리지 목표
- **security.mdc**: 인증/권한, 입력 검증, 보안 헤더

### Deployment (배포 및 인프라)
- **ci-cd.mdc**: GitHub Actions, Docker, Kubernetes 배포

## 🚀 사용법

### 1. 규칙 적용
Cursor 에디터에서 각 `.mdc` 파일의 규칙이 자동으로 적용됩니다.

### 2. 규칙 우선순위
- **High**: 항상 적용되어야 하는 핵심 규칙
- **Medium**: 일반적인 상황에서 적용되는 규칙
- **Low**: 선택적으로 적용할 수 있는 규칙

### 3. 파일 범위
각 규칙은 `globs` 패턴을 통해 적용 범위를 지정합니다:
- `**/*.py`: 모든 Python 파일
- `**/tests/**/*`: 테스트 파일들
- `**/api/**/*`: API 관련 파일들

## 🔧 커스터마이징

### 규칙 추가
새로운 규칙을 추가하려면:
1. 적절한 카테고리 폴더에 `.mdc` 파일 생성
2. 표준 형식에 따라 규칙 작성
3. `globs` 패턴으로 적용 범위 지정

### 규칙 수정
기존 규칙을 수정하려면:
1. 해당 `.mdc` 파일 편집
2. 변경사항을 팀과 공유
3. 필요시 문서 업데이트

## 📋 규칙 형식

각 `.mdc` 파일은 다음 구조를 따릅니다:

```markdown
---
description: 규칙 설명
globs: [적용할 파일 패턴]
alwaysApply: true|false
priority: high|medium|low
---

# 규칙 제목

## Objective
규칙의 목적과 가치

## Context
적용 컨텍스트와 기술적 배경

## Rules
구체적인 규칙과 예시

## Exceptions
규칙이 적용되지 않는 경우
```

## 🤝 팀 협업

### 규칙 리뷰
- 새로운 규칙 추가 시 팀 리뷰 진행
- 정기적인 규칙 업데이트 및 개선
- 팀 피드백 반영

### 규칙 공유
- 규칙 변경사항을 팀원들과 공유
- 규칙 적용 결과 및 개선점 논의
- 지속적인 규칙 품질 향상

## 📚 추가 리소스

- [Cursor 공식 문서](https://docs.cursor.com/)
- [Python PEP 8 스타일 가이드](https://www.python.org/dev/peps/pep-0008/)
- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [SQLAlchemy 공식 문서](https://docs.sqlalchemy.org/)

---

**마지막 업데이트**: 2024년 12월
**버전**: 1.0.0 