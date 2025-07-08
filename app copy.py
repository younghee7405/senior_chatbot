# app.py - 메인 Flask 애플리케이션
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import logging
from typing import List, Dict, Any
import openai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import TextLoader
from langchain.schema import Document
import sqlite3
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 앱 초기화
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 확장 기능 초기화
db = SQLAlchemy(app)
CORS(app)

# OpenAI API 키 설정 (환경변수에서 가져오기)
Gemini.api_key = os.getenv('AIzaSyDV_pS42f6NRMNFbjCsxXUlUUhWDc03b5s')

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

# RAG 시스템 클래스
class SeniorJobRAG:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        self.initialize_knowledge_base()
    
    def initialize_knowledge_base(self):
        """노인 일자리 관련 지식 베이스 초기화"""
        knowledge_data = [
            {
                "title": "공익활동형 일자리",
                "content": """
                공익활동형 일자리는 노인의 경험과 지식을 활용하여 사회에 기여하는 일자리입니다.
                
                주요 활동:
                - 초등학교 급식지원: 학교 급식실에서 배식 및 정리 업무
                - 교통안전 캠페인: 스쿨존 및 횡단보도 교통안전 지도
                - 환경정비 활동: 공원, 하천 청소 및 환경 보호 활동
                - 복지시설 지원: 경로당, 복지관 운영 지원
                - 상담 및 교육: 생활상담, 문해교육 지원
                
                참여 조건:
                - 만 60세 이상
                - 기초연금 수급자 우대
                - 건강상태 양호
                - 성실하고 책임감 있는 분
                
                급여 및 근무:
                - 월 27만원 내외 (활동비 지급)
                - 월 30시간 내외 활동
                - 주 3일, 1일 3시간 내외
                """
            },
            {
                "title": "사회서비스형 일자리",
                "content": """
                사회서비스형 일자리는 노인의 전문성과 경험을 활용하여 사회서비스를 제공하는 일자리입니다.
                
                주요 서비스:
                - 가사간병 서비스: 독거노인, 중증환자 가사 및 간병 지원
                - 시설환경 개선: 공공시설 환경 개선 및 유지보수
                - 교육강사 지원: 평생교육, 취미활동 강사
                - 상담서비스: 노인상담, 생활상담 전문가
                - 보육지원: 어린이집, 유치원 보조교사
                
                참여 조건:
                - 만 60세 이상
                - 해당 분야 경험 또는 자격증 보유 우대
                - 건강상태 양호
                - 서비스 마인드와 책임감
                
                급여 및 근무:
                - 월 60~80만원
                - 월 60시간 내외 근무
                - 주 5일, 1일 3시간 내외
                """
            },
            {
                "title": "시장형 사업단",
                "content": """
                시장형 사업단은 노인이 주체가 되어 운영하는 수익창출형 일자리입니다.
                
                주요 사업:
                - 매점 운영: 공공기관, 학교 내 매점 운영
                - 농산물 판매: 직거래 장터, 농산물 가공 및 판매
                - 세탁업 운영: 지역 세탁소, 청소업체 운영
                - 제조업 참여: 수공예품, 전통식품 제조
                - 카페 운영: 실버카페, 북카페 운영
                
                참여 조건:
                - 만 60세 이상
                - 사업 경험 또는 관련 기술 보유
                - 자립의지와 기업가 정신
                - 팀워크와 협력 정신
                
                급여 및 근무:
                - 최저임금 이상 (수익에 따라 변동)
                - 주 5일, 1일 4~6시간
                - 사업 성과에 따른 인센티브
                """
            },
            {
                "title": "취업알선형 일자리",
                "content": """
                취업알선형 일자리는 민간기업과의 연계를 통해 노인의 경력과 전문성을 활용하는 일자리입니다.
                
                주요 직종:
                - 사무관리: 경리, 총무, 인사 업무 지원
                - 영업판매: 매장 판매원, 영업사원
                - 보안관리: 아파트, 사무실 경비
                - 서비스업: 청소, 배달, 운전 업무
                - 전문직: 상담, 컨설팅, 교육 강사
                
                참여 조건:
                - 만 60세 이상
                - 해당 분야 경력 보유
                - 건강상태 양호
                - 기업 요구사항 충족
                
                급여 및 근무:
                - 해당 기업 급여 기준
                - 기업별 근무시간 상이
                - 4대 보험 가입 가능
                """
            },
            {
                "title": "신청 방법 및 절차",
                "content": """
                노인 일자리 신청 방법과 절차를 안내합니다.
                
                신청 방법:
                1. 방문 신청
                   - 거주지 시니어클럽
                   - 노인복지관
                   - 구청/동사무소 노인일자리 담당부서
                
                2. 온라인 신청
                   - 노인일자리 통합정보시스템 (www.seniorcity.go.kr)
                   - 지역별 노인일자리 홈페이지
                
                신청 절차:
                1. 신청서 작성 및 제출
                2. 서류 심사
                3. 면접 및 적성 검사
                4. 건강진단 (필요시)
                5. 선발 및 배치
                6. 교육 및 오리엔테이션
                7. 활동 시작
                
                준비 서류:
                - 신분증 (주민등록증, 운전면허증 등)
                - 주민등록등본 (최근 3개월 이내)
                - 건강진단서 (해당 사업 참여시)
                - 자격증 또는 경력증명서 (해당자)
                - 통장사본 (급여 지급용)
                
                신청 시기:
                - 연중 수시 접수
                - 주요 모집시기: 2월, 8월
                - 사업별 모집 공고 확인 필요
                """
            }
        ]
        
        # 문서 생성 및 벡터화
        documents = []
        for data in knowledge_data:
            doc = Document(
                page_content=data["content"],
                metadata={"title": data["title"]}
            )
            documents.append(doc)
        
        # 문서 분할
        splits = self.text_splitter.split_documents(documents)
        
        # 벡터 저장소 생성
        self.vectorstore = FAISS.from_documents(splits, self.embeddings)
        
        logger.info(f"RAG 시스템 초기화 완료: {len(splits)}개 문서 청크 생성")
    
    def search_relevant_info(self, query: str, k: int = 3) -> List[str]:
        """관련 정보 검색"""
        if not self.vectorstore:
            return []
        
        # 유사도 검색
        docs = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
    
    def generate_response(self, user_query: str, conversation_history: List[Dict]) -> str:
        """RAG 기반 응답 생성"""
        try:
            # 관련 정보 검색
            relevant_info = self.search_relevant_info(user_query)
            
            # 컨텍스트 구성
            context = "\n\n".join(relevant_info)
            
            # 대화 기록 구성
            history_text = ""
            for msg in conversation_history[-3:]:  # 최근 3개 대화만 사용
                history_text += f"사용자: {msg.get('user_message', '')}\n"
                history_text += f"챗봇: {msg.get('bot_response', '')}\n"
            
            # 프롬프트 구성
            prompt = f"""
            당신은 노인 일자리 상담 전문가입니다. 친절하고 정확한 정보를 제공해주세요.
            
            관련 정보:
            {context}
            
            이전 대화:
            {history_text}
            
            사용자 질문: {user_query}
            
            위 정보를 바탕으로 사용자의 질문에 친절하고 정확하게 답변해주세요.
            답변할 때는 다음 사항을 고려해주세요:
            1. 노인분들이 이해하기 쉽게 설명
            2. 구체적인 정보와 예시 제공
            3. 추가 도움이 필요한 경우 안내
            4. 이모지를 적절히 사용하여 친근감 표현
            """
            
            # OpenAI API 호출
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 노인 일자리 상담 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            return "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

# RAG 시스템 인스턴스 생성
rag_system = SeniorJobRAG()

# 라우트 정의
@app.route('/')
def index():
    """메인 페이지"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>노인 일자리 상담 챗봇 API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            .method { color: #2196F3; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏢 노인 일자리 상담 챗봇 API</h1>
            <p>노인 일자리 상담을 위한 RAG 기반 챗봇 서비스입니다.</p>
            
            <h2>API 엔드포인트</h2>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> /api/chat</h3>
                <p>챗봇과 대화하기</p>
                <pre>{
    "message": "노인 일자리 종류가 어떻게 되나요?",
    "session_id": "session_123"
}</pre>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/conversations</h3>
                <p>대화 기록 조회</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/jobs</h3>
                <p>일자리 정보 조회</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/health</h3>
                <p>서버 상태 확인</p>
            </div>
        </div>
    </body>
    </html>
    """)

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
        recent_conversations = Conversation.query.filter_by(
            session_id=session_id
        ).order_by(Conversation.timestamp.desc()).limit(5).all()
        
        conversation_history = [conv.to_dict() for conv in recent_conversations]
        
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
        
        query = Conversation.query
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        conversations = query.order_by(
            Conversation.timestamp.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'conversations': [conv.to_dict() for conv in conversations.items],
            'total': conversations.total,
            'pages': conversations.pages,
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
        
        query = JobInfo.query
        
        if work_type:
            query = query.filter_by(work_type=work_type)
        
        if location:
            query = query.filter(JobInfo.location.contains(location))
        
        jobs = query.all()
        
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
        
        # 샘플 일자리 데이터 추가
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
        if JobInfo.query.count() == 0:
            for job_data in sample_jobs:
                job = JobInfo(**job_data)
                db.session.add(job)
            
            db.session.commit()
            logger.info("샘플 데이터가 추가되었습니다.")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)