# app.py - 메인 Flask 애플리케이션
from flask import Flask, request, jsonify, render_template_string, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import logging
from typing import List, Dict, Any

# --- Gemini 및 LangChain 관련 임포트 변경 ---
# import openai # OpenAI 라이브러리 대신 Gemini 관련 라이브러리 사용
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings # Gemini 모델 임포트
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS # Langchain 0.1.0 이후 langchain.vectorstores에서 langchain_community.vectorstores로 변경
from langchain_community.document_loaders import CSVLoader # CSV 로더 임포트
from langchain.schema import Document # Document 클래스 임포트
from dotenv import load_dotenv # .env 파일 로드를 위해 추가

# .env 파일 로드 (가장 상단에 위치하여 환경 변수를 먼저 로드)
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 앱 초기화
app = Flask(__name__)
# SECRET_KEY를 .env에서 로드하도록 변경
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-fallback-secret-key-please-change')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 확장 기능 초기화
db = SQLAlchemy(app)
CORS(app)

# Gemini API 키는 ChatGoogleGenerativeAI와 GoogleGenerativeAIEmbeddings가 내부적으로
# 환경 변수 GOOGLE_API_KEY를 참조하므로, 여기서 직접 설정할 필요가 없습니다.
# Gemini.api_key = os.getenv('AIzaSyDV_pS42f6NRMNFbjCsxXUlUUhWDc03b5s') # 이 줄은 삭제하거나 주석 처리

# 데이터베이스 모델
class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_agent = db.Column(db.String(500))

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'bot_response': self.bot_response,
            'timestamp': self.timestamp.isoformat(),
            'user_agent': self.user_agent
        }

class JobInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    salary = db.Column(db.String(100))
    work_type = db.Column(db.String(50))
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# RAG 시스템 클래스 (CSV 파일 로딩 및 Gemini 임베딩/모델 사용)
class SeniorJobRAG:
    def __init__(self):
        # OpenAIEmbeddings 대신 GoogleGenerativeAIEmbeddings 사용
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, # CSV 데이터에 맞게 청크 사이즈 조정
            chunk_overlap=50,
            length_function=len
        )
        # Gemini LLM 모델 초기화
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7) # 또는 "gemini-1.5-pro", "gemini-1.5-flash"
        self.initialize_knowledge_base()

    def initialize_knowledge_base(self):
        """CSV 파일에서 지식 베이스 초기화"""
        data_path = "data" # 데이터 폴더 경로
        all_documents = []

        # 데이터 폴더가 없으면 생성
        if not os.path.exists(data_path):
            os.makedirs(data_path)
            logger.warning(f"경고: '{data_path}' 폴더가 없어 생성했습니다. CSV 파일을 넣어주세요.")
            self.vectorstore = FAISS.from_documents([], self.embeddings)
            return

        # 데이터 폴더 내의 모든 CSV 파일 찾기
        csv_files = [f for f in os.listdir(data_path) if f.endswith('.csv')]

        if not csv_files:
            logger.warning(f"경고: '{data_path}' 폴더에 CSV 파일이 없습니다. 챗봇이 답변할 정보가 제한될 수 있습니다.")
            self.vectorstore = FAISS.from_documents([], self.embeddings)
            return

        for csv_file in csv_files:
            full_csv_path = os.path.join(data_path, csv_file)
            logger.info(f"{full_csv_path} 파일 로딩 중...")

            try:
                loader = CSVLoader(
                    file_path=full_csv_path,
                    # encoding="utf-8",
                    encoding="euc-kr",
                    csv_args={
                        "delimiter": ",",
                    },
                    metadata_columns=['직업명'] # CSV 컬럼명에 맞게 설정
                )
                documents = loader.load()
                logger.info(f"{len(documents)}개의 직업 정보 로드 완료. (파일: {csv_file})")
                all_documents.extend(documents)
            except Exception as e:
                logger.error(f"오류: '{csv_file}' 파일 로딩 중 문제가 발생했습니다: {e}")
                logger.error(f"파일 경로: {full_csv_path}, 인코딩: utf-8")
                logger.error("CSV 파일의 형식이나 컬럼명, 인코딩을 확인해주세요.")
                continue # 다음 파일로 넘어감

        if not all_documents:
            logger.error("모든 CSV 파일에서 문서를 로드하지 못했습니다. RAG 시스템을 구축할 수 없습니다.")
            self.vectorstore = FAISS.from_documents([], self.embeddings)
            return

        logger.info(f"총 {len(all_documents)}개의 통합 문서 생성 완료.")

        # 문서 분할
        splits = self.text_splitter.split_documents(all_documents)

        # 벡터 저장소 생성
        self.vectorstore = FAISS.from_documents(splits, self.embeddings)

        logger.info(f"RAG 시스템 초기화 완료: {len(splits)}개 문서 청크 생성")

    def search_relevant_info(self, query: str, k: int = 3) -> List[str]:
        """관련 정보 검색"""
        if not self.vectorstore:
            logger.warning("벡터 저장소가 초기화되지 않았습니다. 관련 정보를 검색할 수 없습니다.")
            return []

        # 유사도 검색
        docs = self.vectorstore.similarity_search(query, k=k)
        # 검색된 문서의 메타데이터도 포함하여 반환 (프롬프트에서 활용 가능)
        return [f"직업명: {doc.metadata.get('직업명', '알 수 없음')}, 신체활동수준: {doc.metadata.get('신체활동수준', '알 수 없음')}, 업무내용: {doc.page_content}" for doc in docs]

    def generate_response(self, user_query: str, conversation_history: List[Dict]) -> str:
        """RAG 기반 응답 생성"""
        try:
            # 관련 정보 검색
            relevant_info_list = self.search_relevant_info(user_query)
            context = "\n\n".join(relevant_info_list)

            # 대화 기록 구성
            history_text = ""
            for msg in conversation_history[-3:]:  # 최근 3개 대화만 사용
                history_text += f"사용자: {msg.get('user_message', '')}\n"
                history_text += f"챗봇: {msg.get('bot_response', '')}\n"

            # 프롬프트 구성
            prompt = f"""
            당신은 노인 일자리 상담 전문가입니다. 친절하고 정확한 정보를 제공해주세요.
            
            관련 정보 (CSV 파일에서 검색된 내용):
            {context}
            
            이전 대화:
            {history_text}
            
            사용자 질문: {user_query}
            
            위 정보를 바탕으로 사용자의 질문에 친절하고 정확하게 답변해주세요.
            특히 사용자가 '다리 아파'와 같이 신체적 부담을 언급하며 직업을 추천해달라고 할 경우,
            제공된 '관련 정보'에서 '신체활동수준'이 '낮음'이거나, '업무내용'을 보았을 때 주로 앉아서 하거나
            신체적 움직임이 적은 직업들을 우선적으로 추천해주세요.
            추천할 직업이 여러 개라면 2~3가지 정도를 예시로 들어 설명해주세요.
            만약 주어진 '관련 정보'에서 답을 찾을 수 없다면, 모른다고 답하고 추가 정보를 요청하거나, 다른 질문을 하도록 안내해주세요.
            불필요한 정보를 추가하지 마세요. 답변은 한국어로 제공해주세요. 이모지를 적절히 사용하여 친근감 표현해주세요.
            """

            # LangChain ChatGoogleGenerativeAI 모델 호출
            response = self.llm.invoke(prompt) # invoke() 메서드 사용 (LangChain 0.1.0 이후 권장)

            return response.content # 응답 객체에서 content 속성 사용

        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            return "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

# RAG 시스템 인스턴스 생성
rag_system = SeniorJobRAG()

# 라우트 정의
@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """채팅 API"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', f'session_{datetime.now().timestamp()}')
        
        if not user_message:
            return jsonify({'error': '메시지가 비어있습니다.'}), 400
        
        # 이전 대화 기록 조회
        # SQLAlchemy 2.0 스타일의 paginate 사용법에 맞게 수정
        recent_conversations_query = db.session.execute(
            db.select(Conversation).filter_by(session_id=session_id).order_by(Conversation.timestamp.desc()).limit(5)
        ).scalars().all()
        
        conversation_history = [conv.to_dict() for conv in recent_conversations_query]
        
        # RAG 시스템으로 응답 생성
        bot_response = rag_system.generate_response(user_message, conversation_history)
        
        # 대화 기록 저장
        conversation = Conversation(
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response,
            user_agent=request.headers.get('User-Agent', '')
        )
        
        db.session.add(conversation)
        db.session.commit()
        
        return jsonify({
            'response': bot_response,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"채팅 API 오류: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """대화 기록 조회"""
    try:
        session_id = request.args.get('session_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = db.select(Conversation)
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        # SQLAlchemy 2.0 스타일의 paginate 사용법에 맞게 수정
        # .paginate()는 SQLAlchemy 2.0에서 쿼리 객체에 직접 적용되지 않고,
        # Flask-SQLAlchemy의 Pagination 객체를 통해 사용됩니다.
        # 여기서는 Flask-SQLAlchemy의 paginate를 직접 사용합니다.
        pagination_object = db.paginate(
            query.order_by(Conversation.timestamp.desc()),
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'conversations': [conv.to_dict() for conv in pagination_object.items],
            'total': pagination_object.total,
            'pages': pagination_object.pages,
            'current_page': page
        })
        
    except Exception as e:
        logger.error(f"대화 기록 조회 오류: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """일자리 정보 조회"""
    try:
        work_type = request.args.get('work_type')
        location = request.args.get('location')
        
        query = db.select(JobInfo)
        
        if work_type:
            query = query.filter_by(work_type=work_type)
        
        if location:
            # SQLAlchemy 2.0에서는 .contains() 대신 .ilike() 또는 .like() 사용
            query = query.filter(JobInfo.location.ilike(f'%{location}%'))
        
        jobs = db.session.execute(query).scalars().all() # SQLAlchemy 2.0 쿼리 실행
        
        return jsonify({
            'jobs': [{
                'id': job.id,
                'title': job.title,
                'description': job.description,
                'requirements': job.requirements,
                'salary': job.salary,
                'work_type': job.work_type,
                'location': job.location,
                'created_at': job.created_at.isoformat()
            } for job in jobs]
        })
        
    except Exception as e:
        logger.error(f"일자리 정보 조회 오류: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

# 데이터베이스 초기화
def init_db():
    """데이터베이스 및 샘플 데이터 초기화"""
    with app.app_context():
        db.create_all()
        
        # 샘플 일자리 데이터 추가 (JobInfo 테이블에만 추가)
        sample_jobs = [
            {
                'title': '초등학교 급식지원',
                'description': '초등학교 급식실에서 배식 및 정리 업무를 담당합니다.',
                'requirements': '만 60세 이상, 건강상태 양호',
                'salary': '월 27만원',
                'work_type': '공익활동형',
                'location': '서울시 전지역'
            },
            {
                'title': '가사간병 서비스',
                'description': '독거노인 및 거동불편한 어르신들의 가사 및 간병을 지원합니다.',
                'requirements': '만 60세 이상, 관련 경험 또는 자격증 우대',
                'salary': '월 60-80만원',
                'work_type': '사회서비스형',
                'location': '서울시 전지역'
            },
            {
                'title': '실버카페 운영',
                'description': '노인복지관 내 카페 운영 및 관리업무를 담당합니다.',
                'requirements': '만 60세 이상, 서비스업 경험 우대',
                'salary': '최저임금 이상',
                'work_type': '시장형',
                'location': '서울시 강남구'
            }
        ]
        
        # 기존 데이터 확인
        if db.session.execute(db.select(JobInfo)).first() is None:
            for job_data in sample_jobs:
                job = JobInfo(**job_data)
                db.session.add(job)
            
            db.session.commit()
            logger.info("샘플 데이터가 추가되었습니다.")

if __name__ == '__main__':
    # 데이터베이스 초기화는 Flask 앱 컨텍스트 내에서 실행되어야 합니다.
    # app.run() 전에 호출합니다.
    init_db()
    # 포트 5000이 사용 중일 수 있으므로 5001로 변경 (이전 오류 해결을 위해)
    app.run(debug=True, host='0.0.0.0', port=5001)
