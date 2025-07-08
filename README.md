# 노인 일자리 상담 챗봇

RAG(Retrieval-Augmented Generation) 기반의 노인 일자리 상담 챗봇 시스템입니다.

## 🌟 주요 기능

- **RAG 기반 지능형 상담**: OpenAI GPT와 FAISS 벡터 검색을 활용한 정확한 답변
- **실시간 채팅**: WebSocket 기반 실시간 대화
- **대화 기록 관리**: SQLite 데이터베이스를 통한 상담 이력 저장
- **반응형 웹 디자인**: 모바일, 태블릿, 데스크톱 지원
- **REST API**: 외부 시스템 연동 가능

## 🚀 시작하기

### 1. 환경 설정

```bash
# 프로젝트 클론
git clone <repository-url>
cd senior-job-chatbot

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts