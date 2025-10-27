// API 기본 설정
const API_BASE = ""; // 환경에 따라 변경

// API 요청 유틸리티
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    
    const defaultOptions = {
        method: options.method || 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };

    if (options.body) {
        defaultOptions.body = options.body;
    }

    try {
        const response = await fetch(url, defaultOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// 알림 표시
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.role = 'alert';
    
    const icon = type === 'success' ? '✓' : 
                 type === 'error' ? '✕' : 
                 type === 'warning' ? '⚠' : 'ℹ';
    
    alertDiv.innerHTML = `
        <span class="alert-icon">${icon}</span>
        <span class="alert-message">${message}</span>
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    // 스타일 추가 (인라인)
    alertDiv.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: white;
        border-left: 4px solid ${
            type === 'success' ? '#10B981' :
            type === 'error' ? '#EF4444' :
            type === 'warning' ? '#F59E0B' : '#3B82F6'
        };
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-radius: 0.375rem;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        min-width: 300px;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(alertDiv);
    
    // 5초 후 자동 제거
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

// 네비게이션 토글 (모바일)
document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
        });
    }
    
    // 현재 페이지 활성화
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.backgroundColor = '#F3F4F6';
            link.style.fontWeight = '600';
        }
    });
});

// 애니메이션 키프레임 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .alert-close {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        color: #6B7280;
        padding: 0;
        margin-left: 0.5rem;
    }
    
    .alert-close:hover {
        color: #111827;
    }
    
    @media (max-width: 768px) {
        .nav-menu.active {
            display: flex;
            flex-direction: column;
            position: absolute;
            top: 64px;
            left: 0;
            right: 0;
            background: white;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 1rem;
        }
    }
`;
document.head.appendChild(style);

// 전역 에러 핸들러
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});

// 유틸리티 함수들
const utils = {
    formatNumber: (num) => num.toLocaleString('ko-KR'),
    formatDate: (dateString) => new Date(dateString).toLocaleDateString('ko-KR'),
    formatDateTime: (dateString) => new Date(dateString).toLocaleString('ko-KR'),
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// 전역으로 export
window.apiRequest = apiRequest;
window.showAlert = showAlert;
window.utils = utils;

