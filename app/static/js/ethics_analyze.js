// Ethics Analyze - 즉시 실행 함수로 스코프 분리
(function() {
    'use strict';
    
    // API 설정
    const API_BASE_URL = '';  // 같은 도메인 사용

    // DOM 요소
    const elements = {
    textInput: document.getElementById('textInput'),
    charCount: document.getElementById('charCount'),
    analyzeBtn: document.getElementById('analyzeBtn'),
    loadingSpinner: document.getElementById('loadingSpinner'),
    resultSection: document.getElementById('resultSection'),
    errorMessage: document.getElementById('errorMessage'),
    analysisTime: document.getElementById('analysisTime'),
    scoreCard: document.getElementById('scoreCard'),
    spamCard: document.getElementById('spamCard'),
    scoreValue: document.getElementById('scoreValue'),
    spamValue: document.getElementById('spamValue'),
    typesContainer: document.getElementById('typesContainer'),
    recommendation: document.getElementById('recommendation')
};

// 유틸리티 함수
const utils = {
    showLoading() {
        elements.loadingSpinner.classList.add('show');
        elements.resultSection.classList.remove('show');
        elements.errorMessage.classList.remove('show');
    },
    
    hideLoading() {
        elements.loadingSpinner.classList.remove('show');
    },
    
    showError(message) {
        elements.errorMessage.textContent = message;
        elements.errorMessage.classList.add('show');
        elements.resultSection.classList.remove('show');
    },
    
    hideError() {
        elements.errorMessage.classList.remove('show');
    },
    
    updateCharCount() {
        const count = elements.textInput.value.length;
        elements.charCount.textContent = count;
        
        if (count > 900) {
            elements.charCount.style.color = '#e74c3c';
        } else if (count > 700) {
            elements.charCount.style.color = '#f39c12';
        } else {
            elements.charCount.style.color = '#7f8c8d';
        }
    },
    
    formatScore(score) {
        return parseFloat(score).toFixed(1);
    },
    
    getScoreClass(score) {
        if (score >= 70) return 'high-risk';
        if (score >= 30) return 'medium-risk';
        return 'low-risk';
    },
    
    getScoreColor(score) {
        if (score >= 70) return '#e74c3c';
        if (score >= 30) return '#f39c12';
        return '#27ae60';
    },
    
    getSpamClass(spam) {
        if (spam >= 70) return 'spam-high';
        if (spam >= 30) return 'spam-medium';
        return 'spam-low';
    },
    
    createTypeTags(types) {
        if (!types || types.length === 0) {
            return '<span class="type-tag type-none">없음</span>';
        }
        
        const typeClassMap = {
            '욕설 및 비방': 'abuse',
            '도배 및 광고': 'spam',
            '없음': 'none'
        };
        
        return types.map(type => {
            const className = typeClassMap[type] || 'none';
            return `<span class="type-tag type-${className}">${type}</span>`;
        }).join('');
    },
    
    getRecommendation(score, spam, types) {
        let recommendation = '';
        
        if (score >= 70) {
            recommendation = `
                <h4><i class="fas fa-exclamation-triangle"></i> 고위험 콘텐츠</h4>
                <p>이 텍스트는 비윤리적 내용이 포함되어 있습니다. 공개 게시나 전송을 자제하시기 바랍니다.</p>
            `;
        } else if (score >= 40) {
            recommendation = `
                <h4><i class="fas fa-exclamation-circle"></i> 주의 필요</h4>
                <p>일부 부적절한 표현이 포함되어 있습니다. 내용을 검토한 후 사용하시기 바랍니다.</p>
            `;
        } else if (spam >= 60) {
            recommendation = `
                <h4><i class="fas fa-spam"></i> 스팸 의심</h4>
                <p>이 텍스트는 스팸으로 분류될 수 있습니다. 상업적 목적이 있다면 명확히 표시하세요.</p>
            `;
        } else {
            recommendation = `
                <h4><i class="fas fa-check-circle"></i> 정상 콘텐츠</h4>
                <p>이 텍스트는 윤리적으로 문제없는 정상적인 내용입니다.</p>
            `;
        }
        
        return recommendation;
    },
    
    formatTime() {
        const now = new Date();
        return now.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
};

// API 호출 함수
const api = {
    async analyzeText(text) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/ethics/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
};

// 분석 함수
const analyzer = {
    async analyze() {
        const text = elements.textInput.value.trim();
        
        if (!text) {
            utils.showError('분석할 텍스트를 입력해주세요.');
            return;
        }
        
        if (text.length > 1000) {
            utils.showError('텍스트는 1000자를 초과할 수 없습니다.');
            return;
        }
        
        try {
            utils.showLoading();
            elements.analyzeBtn.disabled = true;
            
            const result = await api.analyzeText(text);
            this.displayResult(result);
            
        } catch (error) {
            console.error('Analysis failed:', error);
            utils.showError('분석 중 오류가 발생했습니다. 서버 상태를 확인해주세요.');
        } finally {
            utils.hideLoading();
            elements.analyzeBtn.disabled = false;
        }
    },
    
    displayResult(result) {
        elements.analysisTime.textContent = utils.formatTime();
        
        const score = parseFloat(result.score);
        const confidence = parseFloat(result.confidence);
        const spam = parseFloat(result.spam);
        
        elements.scoreValue.innerHTML = `${utils.formatScore(score)} <small>(${utils.formatScore(confidence)})</small>`;
        elements.spamValue.innerHTML = `${utils.formatScore(spam)} <small>(${utils.formatScore(confidence)})</small>`;
        
        elements.scoreCard.className = `score-card ${utils.getScoreClass(score)}`;
        elements.spamCard.className = `score-card ${utils.getSpamClass(spam)}`;
        
        elements.typesContainer.innerHTML = utils.createTypeTags(result.types);
        elements.recommendation.innerHTML = utils.getRecommendation(score, spam, result.types);
        
        elements.resultSection.classList.add('show');
        utils.hideError();
        
        elements.resultSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    }
};

// 이벤트 리스너
const eventListeners = {
    init() {
        elements.textInput.addEventListener('input', () => {
            utils.updateCharCount();
            utils.hideError();
        });
        
        elements.analyzeBtn.addEventListener('click', () => {
            analyzer.analyze();
        });
        
        elements.textInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                analyzer.analyze();
            }
        });
        
        utils.updateCharCount();
    }
};

// 초기화
const app = {
    init() {
        eventListeners.init();
        elements.textInput.focus();
    }
};

    // 초기화 실행
    document.addEventListener('DOMContentLoaded', () => {
        app.init();
    });
})();
