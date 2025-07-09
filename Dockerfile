# 베이스 이미지 (Python 3.9 버전은 faiss-cpu와 잘 호환됨)
FROM python:3.9-slim

# 시스템 패키지 설치 (Faiss, SWIG 관련 라이브러리 포함)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    swig \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 환경 변수 (Render에서 자동으로 $PORT 지정됨)
ENV PORT=5000

# WSGI 서버로 실행
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "wsgi:app"]

