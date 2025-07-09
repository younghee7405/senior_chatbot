# 베이스 이미지 (faiss-cpu와 호환되는 Python 3.9 전체 이미지)
FROM python:3.9

# 필수 시스템 패키지 설치 (faiss, swig 등 컴파일 도구 포함)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    swig \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt ./

# pip 업그레이드 및 의존성 설치 (LangChain 충돌 방지용 옵션 포함)
RUN pip install --upgrade pip setuptools && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# 전체 앱 코드 복사
COPY . .

# Render에서 $PORT 환경변수를 자동 주입받음
ENV PORT=5000

# Flask 앱 실행 (app.py 내에 app = Flask(...) 인스턴스가 존재해야 함)
CMD gunicorn --bind 0.0.0.0:$PORT app:app
