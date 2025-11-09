// Ethics Analyze - 즉시 실행 함수로 스코프 분리
(function() {
    'use strict';
    
    // API 설정
    const API_BASE_URL = '';  // 같은 도메인 사용
    
    // 전역 변수 (스코프 내)
    let detailedAnalysisData = null;

    // DOM 요소
    const elements = {
    textInput: document.getElementById('textInput'),
    charCount: document.getElementById('charCount'),
    analyzeBtn: document.getElementById('analyzeBtn'),
    detailBtn: document.getElementById('detailBtn'),
    loadingSpinner: document.getElementById('loadingSpinner'),
    resultSection: document.getElementById('resultSection'),
    errorMessage: document.getElementById('errorMessage'),
    analysisTime: document.getElementById('analysisTime'),
    scoreCard: document.getElementById('scoreCard'),
    spamCard: document.getElementById('spamCard'),
    scoreValue: document.getElementById('scoreValue'),
    spamValue: document.getElementById('spamValue'),
    typesContainer: document.getElementById('typesContainer'),
    recommendation: document.getElementById('recommendation'),
    detailSection: document.getElementById('detailSection'),
    detailBertScore: document.getElementById('detailBertScore'),
    detailBertConf: document.getElementById('detailBertConf'),
    detailLlmScore: document.getElementById('detailLlmScore'),
    detailLlmConf: document.getElementById('detailLlmConf'),
    detailProfanityBoost: document.getElementById('detailProfanityBoost'),
    detailBertWeight: document.getElementById('detailBertWeight'),
    detailLlmWeight: document.getElementById('detailLlmWeight'),
    detailBaseScore: document.getElementById('detailBaseScore'),
    detailProfanityBoost2: document.getElementById('detailProfanityBoost2'),
    detailFinalScore: document.getElementById('detailFinalScore'),
    detailLlmSpam: document.getElementById('detailLlmSpam'),
    detailRuleSpam: document.getElementById('detailRuleSpam'),
    detailSpamLlmWeight: document.getElementById('detailSpamLlmWeight'),
    detailSpamRuleWeight: document.getElementById('detailSpamRuleWeight'),
    detailFinalSpam: document.getElementById('detailFinalSpam'),
    ragSummary: document.getElementById('ragSummary'),
    ragSummaryText: document.getElementById('ragSummaryText'),
    ragSummaryCases: document.getElementById('ragSummaryCases'),
    detailRagCard: document.getElementById('ragDetailCard'),
    detailRagEnabled: document.getElementById('detailRagEnabled'),
    detailRagApplied: document.getElementById('detailRagApplied'),
    detailRagWeight: document.getElementById('detailRagWeight'),
    detailRagCount: document.getElementById('detailRagCount'),
    detailRagMaxSim: document.getElementById('detailRagMaxSim'),
    detailRagAdjustedScore: document.getElementById('detailRagAdjustedScore'),
    detailRagAdjustedSpam: document.getElementById('detailRagAdjustedSpam'),
    detailRagCases: document.getElementById('detailRagCases'),
    ragSummaryStatus: document.getElementById('ragSummaryStatus'),
    ragSummaryCount: document.getElementById('ragSummaryCount'),
    ragSummaryMaxSim: document.getElementById('ragSummaryMaxSim'),
    ragSummaryWeight: document.getElementById('ragSummaryWeight'),
    ragSummaryAdjustedScore: document.getElementById('ragSummaryAdjustedScore')
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
        const value = parseFloat(score);
        if (Number.isNaN(value)) {
            return '-';
        }
        return value.toFixed(1);
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
    },

    escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    formatBoolean(flag) {
        return flag ? '예' : '아니오';
    },

    formatPercentage(value) {
        if (isNaN(value)) return '-';
        // 백엔드에서 이미 0-100 범위로 전달됨 (0-1 범위가 아님)
        return `${parseFloat(value).toFixed(1)}%`;
    },

    formatWeight(value) {
        if (value === null || value === undefined) return '-';
        const number = Number(value);
        if (Number.isNaN(number)) return '-';
        return number.toFixed(2);
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
        const spamConfidence = parseFloat(result.spam_confidence || result.confidence);
        
        elements.scoreValue.innerHTML = `${utils.formatScore(score)} <small>(${utils.formatScore(confidence)})</small>`;
        elements.spamValue.innerHTML = `${utils.formatScore(spam)} <small>(${utils.formatScore(spamConfidence)})</small>`;
        
        elements.scoreCard.className = `score-card ${utils.getScoreClass(score)}`;
        elements.spamCard.className = `score-card ${utils.getSpamClass(spam)}`;
        
        elements.typesContainer.innerHTML = utils.createTypeTags(result.types);
        elements.recommendation.innerHTML = utils.getRecommendation(score, spam, result.types);
        
        // 상세 분석 데이터 저장
        detailedAnalysisData = result.detailed || {};
        const ragData = detailedAnalysisData.rag || null;
        console.log('[분석 결과] 상세 데이터 저장:', detailedAnalysisData);
        
        // 상세 분석 버튼 표시
        if (elements.detailBtn) {
            elements.detailBtn.style.display = 'inline-block';
            console.log('[분석 결과] 상세분석 버튼 표시됨');
        } else {
            console.error('[분석 결과] 상세분석 버튼 요소를 찾을 수 없습니다');
        }
        
        // 상세 섹션 숨기기 (새 분석 시)
        if (elements.detailSection) {
            elements.detailSection.style.display = 'none';
        }

        // RAG 요약 표시
        if (elements.ragSummary) {
            if (ragData && ragData.enabled && ragData.similar_cases_count > 0) {
                const weightText = utils.formatWeight(ragData.adjustment_weight);
                const appliedText = ragData.adjustment_applied
                    ? `보정 적용 (가중치 ${weightText})`
                    : '보정은 적용되지 않았습니다';
                elements.ragSummaryText.innerHTML = `유사 사례 <strong>${ragData.similar_cases_count}</strong>건을 참조했습니다. ${appliedText}.`;

                if (elements.ragSummaryStatus) {
                    elements.ragSummaryStatus.textContent = ragData.adjustment_applied ? '보정 적용됨' : '보정 참고만 함';
                    elements.ragSummaryStatus.classList.toggle('inactive', !ragData.adjustment_applied);
                }

                if (elements.ragSummaryCount) {
                    elements.ragSummaryCount.textContent = ragData.similar_cases_count;
                }

                if (elements.ragSummaryMaxSim) {
                    elements.ragSummaryMaxSim.textContent = utils.formatPercentage(ragData.max_similarity);
                }

                if (elements.ragSummaryWeight) {
                    elements.ragSummaryWeight.textContent = ragData.adjustment_applied ? weightText : '-';
                }

                if (elements.ragSummaryAdjustedScore) {
                    const adjustedScoreText = ragData.adjustment_applied && ragData.adjusted_score !== null
                        ? utils.formatScore(ragData.adjusted_score)
                        : '-';
                    elements.ragSummaryAdjustedScore.textContent = adjustedScoreText;
                }
 
                if (elements.ragSummaryCases) {
                    const summaryCases = (ragData.similar_cases || []).slice(0, 3);
                    if (summaryCases.length) {
                        const listHtml = summaryCases.map((item, idx) => {
                            return `
                                <li>
                                    <strong>${idx + 1}.</strong>
                                    <span class="rag-case-sentence">${utils.escapeHtml(item.sentence)}</span>
                                    <span class="rag-case-meta">(유사도 ${utils.formatPercentage(item.similarity)} · 신뢰도 ${utils.formatScore(item.confidence)})</span>
                                </li>
                            `;
                        }).join('');
                        elements.ragSummaryCases.innerHTML = listHtml;
                    } else {
                        elements.ragSummaryCases.innerHTML = '<li>표시할 유사 사례가 없습니다.</li>';
                    }
                }

                elements.ragSummary.style.display = 'block';
            } else {
                elements.ragSummary.style.display = 'none';
                if (elements.ragSummaryStatus) {
                    elements.ragSummaryStatus.textContent = 'RAG 데이터 없음';
                    elements.ragSummaryStatus.classList.add('inactive');
                }
            }
        }

        elements.resultSection.classList.add('show');
        utils.hideError();
        
        elements.resultSection.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
    },
    
    showDetailedAnalysis() {
        console.log('[상세분석] 버튼 클릭됨');
        
        if (!detailedAnalysisData) {
            console.error('[상세분석] detailedData가 없습니다');
            alert('상세 분석 데이터를 찾을 수 없습니다. 먼저 분석을 실행해주세요.');
            return;
        }
        
        console.log('[상세분석] 데이터:', detailedAnalysisData);
        
        const d = detailedAnalysisData || {};
        const rag = d.rag || null;
        
        try {
            // 비윤리 점수 상세
            elements.detailBertScore.textContent = d.bert_score;
            elements.detailBertConf.textContent = d.bert_confidence;
            elements.detailLlmScore.textContent = d.llm_score;
            elements.detailLlmConf.textContent = d.llm_confidence;
            elements.detailProfanityBoost.textContent = d.profanity_boost;
            elements.detailBertWeight.textContent = d.weights.bert;
            elements.detailLlmWeight.textContent = d.weights.llm;
            elements.detailBaseScore.textContent = d.base_score;
            elements.detailProfanityBoost2.textContent = d.profanity_boost;
            elements.detailFinalScore.textContent = (d.base_score + d.profanity_boost).toFixed(1);
            
            // 스팸 점수 상세
            elements.detailLlmSpam.textContent = d.llm_spam_score;
            elements.detailRuleSpam.textContent = d.rule_spam_score;
            elements.detailSpamLlmWeight.textContent = d.spam_weights.llm;
            elements.detailSpamRuleWeight.textContent = d.spam_weights.rule;
            
            const finalSpam = (d.llm_spam_score * d.spam_weights.llm + d.rule_spam_score * d.spam_weights.rule).toFixed(1);
            elements.detailFinalSpam.textContent = finalSpam;
            
            // RAG 상세 정보
            if (elements.detailRagCard) {
                if (rag && rag.enabled && rag.similar_cases_count !== undefined) {
                    elements.detailRagCard.style.display = 'block';
                    elements.detailRagEnabled.textContent = utils.formatBoolean(rag.enabled);
                    elements.detailRagApplied.textContent = utils.formatBoolean(rag.adjustment_applied);
                    const ragWeightValue = utils.formatWeight(rag.adjustment_weight);
                    elements.detailRagWeight.textContent = rag.adjustment_applied ? ragWeightValue : '-';
                    elements.detailRagCount.textContent = rag.similar_cases_count;
                    elements.detailRagMaxSim.textContent = utils.formatPercentage(rag.max_similarity);
                    elements.detailRagAdjustedScore.textContent = rag.adjustment_applied && rag.adjusted_score !== null ? utils.formatScore(rag.adjusted_score) : '-';
                    elements.detailRagAdjustedSpam.textContent = rag.adjustment_applied && rag.adjusted_spam_score !== null ? utils.formatScore(rag.adjusted_spam_score) : '-';

                    if (elements.detailRagCases) {
                        const cases = rag.similar_cases || [];
                        if (cases.length) {
                            const caseListHtml = cases.map((item, idx) => `
                                <div class="rag-case-item">
                                    <div class="rag-case-title">사례 ${idx + 1}</div>
                                    <div class="rag-case-sentence">${utils.escapeHtml(item.sentence)}</div>
                                    <div class="rag-case-meta">
                                        유사도 ${utils.formatPercentage(item.similarity)} · 비윤리 ${utils.formatScore(item.immoral_score)} · 스팸 ${utils.formatScore(item.spam_score)} · 신뢰도 ${utils.formatScore(item.confidence)}
                                        ${item.confirmed ? ' · 관리자 확인' : ''}
                                    </div>
                                </div>
                            `).join('');
                            elements.detailRagCases.innerHTML = caseListHtml;
                        } else {
                            elements.detailRagCases.innerHTML = '<p>참조된 유사 사례가 없습니다.</p>';
                        }
                    }
                } else {
                    elements.detailRagCard.style.display = 'none';
                }
            }

            // 상세 섹션 표시
            elements.detailSection.style.display = 'block';
            
            console.log('[상세분석] 상세 섹션 표시 완료');
            
            // 상세 섹션으로 스크롤
            setTimeout(() => {
                elements.detailSection.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'start' 
                });
            }, 100);
            
        } catch (error) {
            console.error('[상세분석] 오류 발생:', error);
            alert('상세 분석 표시 중 오류가 발생했습니다: ' + error.message);
        }
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
        
        elements.detailBtn.addEventListener('click', () => {
            console.log('[이벤트] 상세분석 버튼 클릭');
            analyzer.showDetailedAnalysis();
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
        console.log('[초기화] 앱 초기화 시작');
        
        // DOM 요소 확인
        console.log('[초기화] detailBtn 요소:', elements.detailBtn);
        console.log('[초기화] detailSection 요소:', elements.detailSection);
        
        if (!elements.detailBtn) {
            console.error('[초기화] 경고: detailBtn 요소를 찾을 수 없습니다');
        }
        if (!elements.detailSection) {
            console.error('[초기화] 경고: detailSection 요소를 찾을 수 없습니다');
        }
        if (!elements.detailRagCard) {
            console.warn('[초기화] RAG 상세 카드 요소를 찾을 수 없습니다');
        }
        
        eventListeners.init();
        elements.textInput.focus();
        
        console.log('[초기화] 앱 초기화 완료');
    }
};

    // 초기화 실행
    document.addEventListener('DOMContentLoaded', () => {
        app.init();
    });
})();
