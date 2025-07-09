# ✅ 1. faiss-cpu와 호환되는 Python 3.9 전체 이미지 사용
FROM python:3.9

# ✅ 2. 필수 시스템 패키지 설치 (Faiss 빌드, LangChain 호환용)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    swig \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# ✅ 3. 앱 디렉토리 설정
WORKDIR /app

# ✅ 4. requirements.txt 복사 및 pip 의존성 설치
COPY requirements.txt ./

# LangChain 및 Gemini 충돌 방지를 위한 pip legacy-resolver 사용
RUN pip install --upgrade pip setuptools && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# ✅ 5. 전체 애플리케이션 코드 복사
COPY . .

# ✅ 6. Render에서 PORT 환경변수 자동 주입
ENV PORT=5000

# ✅ 7. Gunicorn WSGI 서버로 앱 실행
# app.py 내부에 `app = Flask(__name__)`가 존재해야 합니다
CMD gunicorn --bind 0.0.0.0:$PORT app:app
