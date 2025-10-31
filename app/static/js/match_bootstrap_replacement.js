/* Bootstrap JavaScript 대체 기능 */

// 모달 클래스
class Modal {
    constructor(element) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.backdrop = null;
        this.isShown = false;
        
        // 모달 이벤트 바인딩
        this.bindEvents();
    }
    
    bindEvents() {
        // 닫기 버튼 이벤트
        const closeButtons = this.element.querySelectorAll('.btn-close, [data-bs-dismiss="modal"]');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.hide());
        });
        
        // ESC 키로 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isShown) {
                this.hide();
            }
        });
    }
    
    show() {
        if (this.isShown) return;
        
        this.isShown = true;
        
        // 백드롭 생성
        this.createBackdrop();
        
        // 모달 표시
        this.element.style.display = 'block';
        this.element.classList.add('show');
        
        // 애니메이션을 위한 약간의 지연
        setTimeout(() => {
            this.element.classList.add('fade');
        }, 10);
        
        // body 스크롤 방지
        document.body.style.overflow = 'hidden';
        
        // 포커스 설정
        this.element.focus();
    }
    
    hide() {
        if (!this.isShown) return;
        
        this.isShown = false;
        
        // 애니메이션
        this.element.classList.remove('show');
        
        setTimeout(() => {
            this.element.style.display = 'none';
            this.element.classList.remove('fade');
            
            // 백드롭 제거
            this.removeBackdrop();
            
            // body 스크롤 복원
            document.body.style.overflow = '';
        }, 150);
    }
    
    createBackdrop() {
        this.backdrop = document.createElement('div');
        this.backdrop.className = 'modal-backdrop';
        this.backdrop.addEventListener('click', () => this.hide());
        document.body.appendChild(this.backdrop);
    }
    
    removeBackdrop() {
        if (this.backdrop) {
            this.backdrop.remove();
            this.backdrop = null;
        }
    }
    
    // 정적 메서드
    static getInstance(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        return el._modalInstance || null;
    }
}

// 탭 클래스
class Tab {
    constructor(element) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.target = this.element.getAttribute('href') || this.element.getAttribute('data-bs-target');
    }
    
    show() {
        // 현재 활성 탭 비활성화
        const currentActiveTab = document.querySelector('.nav-tabs .nav-link.active');
        const currentActivePane = document.querySelector('.tab-pane.show.active');
        
        if (currentActiveTab) {
            currentActiveTab.classList.remove('active');
        }
        if (currentActivePane) {
            currentActivePane.classList.remove('show', 'active');
        }
        
        // 새 탭 활성화
        this.element.classList.add('active');
        
        // 새 패널 활성화
        const targetPane = document.querySelector(this.target);
        if (targetPane) {
            targetPane.classList.add('show', 'active');
        }
    }
}

// 알림 클래스 (Alert)
class Alert {
    constructor(element) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.bindEvents();
    }
    
    bindEvents() {
        const closeButton = this.element.querySelector('.btn-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => this.close());
        }
    }
    
    close() {
        this.element.classList.add('fade');
        setTimeout(() => {
            this.element.remove();
        }, 150);
    }
}

// 전역 bootstrap 객체 생성 (기존 코드 호환성을 위해)
window.bootstrap = {
    Modal: Modal,
    Tab: Tab,
    Alert: Alert
};

// 모달 인스턴스 관리
document.addEventListener('DOMContentLoaded', function() {
    // 모든 모달에 인스턴스 생성
    document.querySelectorAll('.modal').forEach(modalEl => {
        modalEl._modalInstance = new Modal(modalEl);
    });
    
    // 탭 클릭 이벤트 처리
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tabEl => {
        tabEl.addEventListener('click', function(e) {
            e.preventDefault();
            const tab = new Tab(this);
            tab.show();
        });
    });
    
    // 알림 자동 초기화
    document.querySelectorAll('.alert').forEach(alertEl => {
        new Alert(alertEl);
    });
});

// 유틸리티 함수들
function showModal(modalSelector) {
    const modal = document.querySelector(modalSelector);
    if (modal && modal._modalInstance) {
        modal._modalInstance.show();
    }
}

function hideModal(modalSelector) {
    const modal = document.querySelector(modalSelector);
    if (modal && modal._modalInstance) {
        modal._modalInstance.hide();
    }
}

function switchTab(tabSelector) {
    const tab = document.querySelector(tabSelector);
    if (tab) {
        const tabInstance = new Tab(tab);
        tabInstance.show();
    }
}

// 드롭다운 기능 (필요시)
class Dropdown {
    constructor(element) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.menu = null;
        this.isShown = false;
        this.bindEvents();
    }
    
    bindEvents() {
        this.element.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggle();
        });
        
        // 외부 클릭시 닫기
        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target) && this.isShown) {
                this.hide();
            }
        });
    }
    
    toggle() {
        this.isShown ? this.hide() : this.show();
    }
    
    show() {
        if (this.isShown) return;
        
        this.menu = this.element.nextElementSibling;
        if (this.menu && this.menu.classList.contains('dropdown-menu')) {
            this.menu.style.display = 'block';
            this.isShown = true;
        }
    }
    
    hide() {
        if (!this.isShown) return;
        
        if (this.menu) {
            this.menu.style.display = 'none';
            this.isShown = false;
        }
    }
}

// 툴팁 기능 (간단한 버전)
class Tooltip {
    constructor(element, options = {}) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.options = {
            title: options.title || this.element.getAttribute('title') || this.element.getAttribute('data-bs-title'),
            placement: options.placement || 'top',
            ...options
        };
        this.tooltip = null;
        this.bindEvents();
    }
    
    bindEvents() {
        this.element.addEventListener('mouseenter', () => this.show());
        this.element.addEventListener('mouseleave', () => this.hide());
    }
    
    show() {
        if (this.tooltip || !this.options.title) return;
        
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tooltip';
        this.tooltip.innerHTML = `<div class="tooltip-inner">${this.options.title}</div>`;
        
        document.body.appendChild(this.tooltip);
        
        // 위치 계산
        const rect = this.element.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        
        let top, left;
        
        switch (this.options.placement) {
            case 'top':
                top = rect.top - tooltipRect.height - 5;
                left = rect.left + (rect.width - tooltipRect.width) / 2;
                break;
            case 'bottom':
                top = rect.bottom + 5;
                left = rect.left + (rect.width - tooltipRect.width) / 2;
                break;
            case 'left':
                top = rect.top + (rect.height - tooltipRect.height) / 2;
                left = rect.left - tooltipRect.width - 5;
                break;
            case 'right':
                top = rect.top + (rect.height - tooltipRect.height) / 2;
                left = rect.right + 5;
                break;
        }
        
        this.tooltip.style.position = 'fixed';
        this.tooltip.style.top = top + 'px';
        this.tooltip.style.left = left + 'px';
        this.tooltip.style.zIndex = '1070';
    }
    
    hide() {
        if (this.tooltip) {
            this.tooltip.remove();
            this.tooltip = null;
        }
    }
}

// bootstrap 객체에 추가
window.bootstrap.Dropdown = Dropdown;
window.bootstrap.Tooltip = Tooltip;
