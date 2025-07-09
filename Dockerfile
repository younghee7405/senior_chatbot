# 베이스 이미지 (Python 3.9 - faiss-cpu와 호환)
FROM python:3.9

# 시스템 패키지 설치 (Faiss 및 빌드 도구)
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
RUN pip install --upgrade pip setuptools && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# 앱 코드 복사
COPY . .

# 환경 변수 설정 (Render에서 자동으로 $PORT 주입됨)
ENV PORT=5000

# WSGI 서버 실행
CMD gunicorn --bind 0.0.0.0:$PORT app:app
