// 전역 변수
let sessionId = null;
let messageCount = 0;
let isLoading = false;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
    generateSessionId();
    updateStats();
    // 챗봇 플로팅 버튼/팝업 이벤트 연결
    setupChatbotPopupEvents();
});

function setupChatbotPopupEvents() {
    const floatingBtn = document.getElementById('chatbotFloatingBtn');
    const popup = document.getElementById('chatbotPopup');
    const closeBtn = document.getElementById('closeChatbotPopup');

    // 팝업 열기
    floatingBtn.addEventListener('click', function() {
        popup.style.display = 'flex';
        floatingBtn.style.display = 'none';
    });
    // 팝업 닫기
    closeBtn.addEventListener('click', function() {
        popup.style.display = 'none';
        floatingBtn.style.display = 'flex';
    });
    // 최초에는 팝업 닫힘, 버튼만 보임
    popup.style.display = 'none';
    floatingBtn.style.display = 'flex';
}

// 세션 ID 생성
function generateSessionId() {
    sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    document.getElementById('currentSession').textContent = sessionId.substring(0, 12) + '...';
}

// 이벤트 리스너 설정
function setupEventListeners() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    
    // 엔터키 이벤트
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 입력 필드 변화 감지
    messageInput.addEventListener('input', function() {
        const hasText = this.value.trim().length > 0;
        sendButton.style.opacity = hasText ? '1' : '0.6';
    });
    
    // 메시지 컨테이너 자동 스크롤
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.addEventListener('scroll', function() {
        // 스크롤이 맨 아래에 있을 때 새 메시지 자동 스크롤
        const isAtBottom = chatMessages.scrollHeight - chatMessages.scrollTop === chatMessages.clientHeight;
        if (isAtBottom) {
            chatMessages.dataset.autoScroll = 'true';
        } else {
            chatMessages.dataset.autoScroll = 'false';
        }
    });
}

// 채팅 초기화
function initializeChat() {
    console.log('채팅 시스템 초기화 완료');
    
    // API 연결 테스트
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            console.log('서버 상태:', data.status);
        })
        .catch(error => {
            console.error('서버 연결 오류:', error);
            showError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
        });
}

// 메시지 전송
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message || isLoading) return;
    
    // 입력 필드 초기화
    messageInput.value = '';
    
    // 사용자 메시지 표시
    addMessage(message, 'user');
    
    // 로딩 상태 표시
    showLoading(true);
    
    try {
        // API 호출
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 봇 응답 표시
        addMessage(data.response, 'bot');
        
        // 통계 업데이트
        messageCount++;
        updateStats();
        
    } catch (error) {
        console.error('메시지 전송 오류:', error);
        addMessage('죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'bot');
    } finally {
        showLoading(false);
    }
}

// 빠른 메시지 전송
function sendQuickMessage(message) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    sendMessage();
}

// 메시지 추가
function addMessage(content, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // 메시지 내용 처리 (마크다운 스타일 지원)
    const formattedContent = formatMessage(content);
    contentDiv.innerHTML = formattedContent;
    
    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    
    // 자동 스크롤
    scrollToBottom();
}

// 메시지 포맷팅
function formatMessage(content) {
    // 줄바꿈 처리
    content = content.replace(/\n/g, '<br>');
    
    // 불릿 포인트 처리
    content = content.replace(/^- (.+)$/gm, '<li>$1</li>');
    content = content.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // 강조 텍스트 처리
    content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // 전화번호 링크 처리
    content = content.replace(/(\d{3,4}-\d{4}|\d{4}-\d{4})/g, '<a href="tel:$1">$1</a>');
    
    return content;
}

// 로딩 상태 표시
function showLoading(show) {
    isLoading = show;
    const loadingOverlay = document.getElementById('loadingOverlay');
    const sendButton = document.getElementById('sendButton');
    
    if (show) {
        loadingOverlay.style.display = 'flex';
        sendButton.style.opacity = '0.6';
        sendButton.style.cursor = 'not-allowed';
    } else {
        loadingOverlay.style.display = 'none';
        sendButton.style.opacity = '1';
        sendButton.style.cursor = 'pointer';
    }
}

// 자동 스크롤
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    
    // 부드러운 스크롤 애니메이션
    chatMessages.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: 'smooth'
    });
}

// 대화 초기화
function clearChat() {
    if (confirm('대화 내용을 모두 삭제하시겠습니까?')) {
        const chatMessages = document.getElementById('chatMessages');
        
        // 기본 환영 메시지만 남기고 모든 메시지 삭제
        const welcomeMessage = chatMessages.querySelector('.bot-message');
        chatMessages.innerHTML = '';
        if (welcomeMessage) {
            chatMessages.appendChild(welcomeMessage);
        }
        
        // 새로운 세션 ID 생성
        generateSessionId();
        
        // 통계 초기화
        messageCount = 0;
        updateStats();
        
        console.log('대화가 초기화되었습니다.');
    }
}

// 통계 업데이트
function updateStats() {
    document.getElementById('totalChats').textContent = messageCount;
}

// 오류 메시지 표시
function showError(message) {
    addMessage(`⚠️ 오류: ${message}`, 'bot');
}

// 유틸리티 함수들
const utils = {
    // 시간 포맷팅
    formatTime: function(date) {
        return date.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    // 텍스트 복사
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            console.log('텍스트가 복사되었습니다.');
        }).catch(err => {
            console.error('복사 실패:', err);
        });
    },
    
    // 모바일 기기 감지
    isMobile: function() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
};

// === 음성 입력(마이크) 기능 ===
function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window)) {
        alert('이 브라우저는 음성 인식을 지원하지 않습니다. 크롬 브라우저를 사용해주세요.');
        return;
    }
    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'ko-KR';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = function() {
        document.getElementById('voiceButton').style.color = '#ff4b4b';
    };
    recognition.onend = function() {
        document.getElementById('voiceButton').style.color = '';
    };
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('messageInput').value = transcript;
        document.getElementById('messageInput').focus();
    };
    recognition.onerror = function(event) {
        alert('음성 인식 중 오류가 발생했습니다: ' + event.error);
    };
    recognition.start();
}

// 페이지 가시성 변경 감지
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('페이지가 숨겨짐');
    } else {
        console.log('페이지가 표시됨');
    }
});

// 오류 처리
window.addEventListener('error', function(e) {
    console.error('전역 오류:', e.error);
});

// 약속 거부 처리
window.addEventListener('unhandledrejection', function(e) {
    console.error('처리되지 않은 Promise 거부:', e.reason);
});