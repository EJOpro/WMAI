// Ethics Dashboard - 즉시 실행 함수로 스코프 분리
(function() {
    'use strict';
    
    // API 설정
    const API_BASE_URL = '';  // 같은 도메인 사용

    // 전역 변수
    let currentPage = 0;
    let currentLimit = 30;
    let currentFilters = {};
    let allLogs = [];
        let originalLogs = [];
        let filteredLogs = [];

const updateCachedLog = (logId, updates = {}) => {
    const applyUpdates = (log) => {
        if (log && log.id === logId) {
            Object.assign(log, updates);
        }
    };

    [originalLogs, filteredLogs, allLogs].forEach((collection) => {
        if (!collection) return;
        if (Array.isArray(collection)) {
            collection.forEach(applyUpdates);
        } else {
            applyUpdates(collection);
        }
    });
};

    // DOM 요소
    const elements = {
    refreshBtn: document.getElementById('refreshBtn'),
    exportBtn: document.getElementById('exportBtn'),
    scoreFilter: document.getElementById('scoreFilter'),
    spamFilter: document.getElementById('spamFilter'),
    dateFilter: document.getElementById('dateFilter'),
    searchInput: document.getElementById('searchInput'),
    applyFilters: document.getElementById('applyFilters'),
    clearFilters: document.getElementById('clearFilters'),
    logsTableBody: document.getElementById('logsTableBody'),
    logCount: document.getElementById('logCount'),
    pageSizeSelect: document.getElementById('pageSizeSelect'),
    firstPage: document.getElementById('firstPage'),
    prevPage: document.getElementById('prevPage'),
    nextPage: document.getElementById('nextPage'),
    lastPage: document.getElementById('lastPage'),
    pageInfo: document.getElementById('pageInfo'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    logModal: document.getElementById('logModal'),
    closeModal: document.getElementById('closeModal'),
    modalBody: document.getElementById('modalBody'),
    deleteModal: document.getElementById('deleteModal'),
    closeDeleteModal: document.getElementById('closeDeleteModal'),
    confirmDelete: document.getElementById('confirmDelete'),
    cancelDelete: document.getElementById('cancelDelete'),
    deleteOldBtn: document.getElementById('deleteOldBtn'),
    deleteOldModal: document.getElementById('deleteOldModal'),
    closeDeleteOldModal: document.getElementById('closeDeleteOldModal'),
    deleteDays: document.getElementById('deleteDays'),
    previewCount: document.getElementById('previewCount'),
    confirmDeleteOld: document.getElementById('confirmDeleteOld'),
    cancelDeleteOld: document.getElementById('cancelDeleteOld'),
    totalCount: document.getElementById('totalCount'),
    highRiskCount: document.getElementById('highRiskCount'),
    spamCount: document.getElementById('spamCount'),
    avgScore: document.getElementById('avgScore'),
    ragStatusTag: document.getElementById('ragStatusTag'),
    ragCaseCount: document.getElementById('ragCaseCount'),
    ragAllCasesCard: document.getElementById('ragAllCasesCard'),
    ragConfirmedCard: document.getElementById('ragConfirmedCard'),
    ragConfirmedCount: document.getElementById('ragConfirmedCount'),
    ragCorrectionCount: document.getElementById('ragCorrectionCount'),
    ragAppliedLogs: document.getElementById('ragAppliedLogs'),
    ragPendingCount: document.getElementById('ragPendingCount'),
    autoBlockedCount: document.getElementById('autoBlockedCount'),
    autoBlockedCard: document.getElementById('autoBlockedCard'),
    ragAvgImmoral: document.getElementById('ragAvgImmoral'),
    ragAvgSpam: document.getElementById('ragAvgSpam'),
    feedbackModal: document.getElementById('feedbackModal'),
    closeFeedbackModal: document.getElementById('closeFeedbackModal'),
    feedbackModalBody: document.getElementById('feedbackModalBody'),
    allCasesModal: document.getElementById('allCasesModal'),
    closeAllCasesModal: document.getElementById('closeAllCasesModal'),
    autoBlockedModal: document.getElementById('autoBlockedModal'),
    closeAutoBlockedModal: document.getElementById('closeAutoBlockedModal'),
    allCasesModalBody: document.getElementById('allCasesModalBody')
};

// 유틸리티 함수
const utils = {
    showLoading() {
        elements.loadingOverlay.classList.add('show');
    },
    
    hideLoading() {
        elements.loadingOverlay.classList.remove('show');
    },
    
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    formatScore(score) {
        const value = parseFloat(score);
        if (Number.isNaN(value)) return '-';
        return value.toFixed(1);
    },
    
    formatNumber(value) {
        if (value === null || value === undefined) return '-';
        const number = Number(value);
        if (Number.isNaN(number)) return '-';
        return number.toLocaleString();
    },
    
    getScoreClass(score) {
        if (score >= 70) return 'score-high';
        if (score >= 30) return 'score-medium';
        return 'score-low';
    },
    
    getSpamClass(spam) {
        if (spam >= 70) return 'spam-high';
        if (spam >= 30) return 'spam-medium';
        return 'spam-low';
    },
    
    createTypeTags(types) {
        if (!types || types.length === 0) return '';
        
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
    
    truncateText(text, maxLength = 50) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    createRagStatus(applied) {
        const isApplied = Boolean(applied);
        const icon = isApplied ? 'fa-check-circle' : 'fa-minus-circle';
        const label = isApplied ? '적용' : '미적용';
        const inactiveClass = isApplied ? '' : ' inactive';
        return `<span class="rag-status-chip${inactiveClass}"><i class="fas ${icon}"></i> ${label}</span>`;
    },

    createAutoBlockStatus(blocked) {
        const isBlocked = Boolean(blocked);
        const icon = isBlocked ? 'fa-bolt' : 'fa-minus-circle';
        const label = isBlocked ? '즉시 차단' : '미적용';
        const chipClass = isBlocked ? 'auto-block-chip active' : 'auto-block-chip inactive';
        return `<span class="${chipClass}"><i class="fas ${icon}"></i> ${label}</span>`;
    },

    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    formatFeedbackLabel(action) {
        const map = {
            'immoral': '비윤리',
            'spam': '스팸',
            'clean': '문제없음'
        };
        return map[action] || '미확정';
    },

    createFeedbackBadge(action) {
        if (!action) {
            return '<span class="feedback-badge feedback-none">미확정</span>';
        }
        const actionClass = {
            'immoral': 'feedback-immoral',
            'spam': 'feedback-spam',
            'clean': 'feedback-clean'
        }[action] || 'feedback-none';
        const label = this.formatFeedbackLabel(action);
        return `<span class="feedback-badge ${actionClass}">${label}</span>`;
    }
};

// rag-status-chip 및 auto-block-chip 스타일이 없는 환경을 위한 폴백 정의
if (!document.querySelector('style[data-rag-chip-fallback]')) {
    const fallbackStyle = document.createElement('style');
    fallbackStyle.setAttribute('data-rag-chip-fallback', 'true');
    fallbackStyle.textContent = `
        .rag-status-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(102, 126, 234, 0.15);
            color: #324cdd;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .rag-status-chip.inactive {
            background: rgba(231, 76, 60, 0.15);
            color: #e74c3c;
        }
        .auto-block-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .auto-block-chip.active {
            background: rgba(255, 193, 7, 0.2);
            color: #f57c00;
            border: 1px solid rgba(255, 193, 7, 0.4);
        }
        .auto-block-chip.inactive {
            background: rgba(158, 158, 158, 0.15);
            color: #757575;
        }
    `;
    document.head.appendChild(fallbackStyle);
}

// API 호출 함수
const api = {
    async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    async getLogs(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return await this.request(`${API_BASE_URL}/api/ethics/logs?${queryString}`);
    },
    
    async getStats(days = 7) {
        return await this.request(`${API_BASE_URL}/api/ethics/logs/stats?days=${days}`);
    },
    
    async deleteLog(logId) {
        return await this.request(`${API_BASE_URL}/api/ethics/logs/${logId}`, {
            method: 'DELETE'
        });
    },
    
    async deleteOldLogs(days) {
        return await this.request(`${API_BASE_URL}/api/ethics/logs/batch/old?days=${days}`, {
            method: 'DELETE'
        });
    },

    async getConfirmedFeedbacks(params = {}) {
        const searchParams = new URLSearchParams(params).toString();
        const basePath = `${API_BASE_URL}/api/admin/ethics/feedback`;
        const url = searchParams ? `${basePath}?${searchParams}` : basePath;
        return await this.request(url);
    }
};

// 데이터 로딩 함수
const dataLoader = {
    async loadStats() {
        try {
            const days = parseInt(elements.dateFilter.value) || 365; // 전체일 때는 365일
            const stats = await api.getStats(days);
            
            elements.totalCount.textContent = stats.total_count.toLocaleString();
            elements.highRiskCount.textContent = stats.high_risk_count.toLocaleString();
            elements.spamCount.textContent = stats.spam_count.toLocaleString();
            elements.avgScore.textContent = utils.formatScore(stats.avg_score);

            const ragStats = stats.rag_stats || {};
            const ragStatus = ragStats.status || 'unknown';

            if (elements.ragStatusTag) {
                const tag = elements.ragStatusTag;
                tag.innerHTML = '<i class="fas fa-circle"></i> ' + (ragStatus === 'active' ? 'RAG 활성' : 'RAG 비활성');
                tag.classList.toggle('offline', ragStatus !== 'active');
            }

            if (elements.ragCaseCount) {
                elements.ragCaseCount.textContent = utils.formatNumber(ragStats.total_documents);
            }
            if (elements.ragConfirmedCount) {
                elements.ragConfirmedCount.textContent = utils.formatNumber(ragStats.confirmed_count);
            }
            if (elements.ragCorrectionCount) {
                const correctionCount = stats.rag_applied_count !== undefined ? stats.rag_applied_count : null;
                elements.ragCorrectionCount.textContent = utils.formatNumber(correctionCount);
            }
            if (elements.ragAppliedLogs) {
                const appliedCount = stats.rag_applied_count !== undefined ? stats.rag_applied_count : null;
                elements.ragAppliedLogs.textContent = utils.formatNumber(appliedCount);
            }
            if (elements.ragPendingCount) {
                elements.ragPendingCount.textContent = utils.formatNumber(ragStats.unconfirmed_count);
            }
            if (elements.autoBlockedCount) {
                const autoBlockedCount = stats.auto_blocked_count !== undefined ? stats.auto_blocked_count : null;
                elements.autoBlockedCount.textContent = utils.formatNumber(autoBlockedCount);
            }
            if (elements.ragAvgImmoral) {
                elements.ragAvgImmoral.textContent = utils.formatScore(ragStats.avg_immoral_score);
            }
            if (elements.ragAvgSpam) {
                elements.ragAvgSpam.textContent = utils.formatScore(ragStats.avg_spam_score);
            }
            
        } catch (error) {
            console.error('Failed to load stats:', error);
            this.showError('통계를 불러오는데 실패했습니다.');
        }
    },
    
    async loadLogs() {
        try {
            utils.showLoading();
            
            // 전체 로그를 가져옴 (클라이언트 사이드 페이지네이션)
            const params = {
                limit: 1000,  // 충분히 큰 값으로 전체 데이터 가져오기
                offset: 0,
                ...currentFilters
            };
            
            const response = await api.getLogs(params);
            originalLogs = response.logs;
            filteredLogs = [...response.logs];
            
            // 첫 페이지 데이터 표시
            const startIndex = currentPage * currentLimit;
            const endIndex = startIndex + currentLimit;
            allLogs = filteredLogs.slice(startIndex, endIndex);
            
            this.renderLogs();
            this.updatePagination(filteredLogs.length);
            
        } catch (error) {
            console.error('Failed to load logs:', error);
            this.showError('로그를 불러오는데 실패했습니다.');
        } finally {
            utils.hideLoading();
        }
    },
    
    renderLogs() {
        const tbody = elements.logsTableBody;
        tbody.innerHTML = '';
        
        if (allLogs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px; color: #7f8c8d;">
                        <i class="fas fa-inbox" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>
                        로그가 없습니다.
                    </td>
                </tr>
            `;
            return;
        }
        
        allLogs.forEach(log => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="id-column">${log.id}</td>
                <td class="date-column">${utils.formatDate(log.created_at)}</td>
                <td class="text-preview" title="${log.text}">${utils.truncateText(log.text || '')}</td>
                <td class="${utils.getScoreClass(log.score)}">${log.score != null ? `${utils.formatScore(log.score)} <br><small>(${utils.formatScore(log.confidence)})</small>` : '-'}</td>
                <td class="${utils.getSpamClass(log.spam)}">${log.spam != null ? `${utils.formatScore(log.spam)} <br><small>(${utils.formatScore(log.spam_confidence)})</small>` : '-'}</td>
                <td class="type-tags">${utils.createTypeTags(log.types)}</td>
                <td class="rag-column">${utils.createRagStatus(log.rag_applied)}</td>
                <td class="auto-block-column">${utils.createAutoBlockStatus(log.auto_blocked)}</td>
                <td class="delete-column">
                    <button class="btn-delete" data-log-id="${log.id}" data-log-text="${log.text.replace(/"/g, '&quot;')}" data-log-score="${log.score}">
                        <i class="fas fa-trash-alt"></i>
                        <span>삭제</span>
                    </button>
                </td>
            `;
            
            // 삭제 버튼 이벤트
            const deleteBtn = row.querySelector('.btn-delete');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteManager.showDeleteModal(log.id, log.text, log.score);
            });
            
            // 행 클릭 이벤트 (상세 보기)
            row.addEventListener('click', () => this.showLogDetail(log));
            tbody.appendChild(row);
        });
    },
    
    updatePagination(totalCount) {
        const totalPages = Math.max(1, Math.ceil(totalCount / currentLimit));
        const currentPageNum = currentPage + 1;
        
        elements.pageInfo.textContent = `${currentPageNum} / ${totalPages}`;
        elements.logCount.textContent = `${totalCount}개`;
        
        // 버튼 활성화/비활성화
        elements.firstPage.disabled = currentPage === 0;
        elements.prevPage.disabled = currentPage === 0;
        elements.nextPage.disabled = currentPage >= totalPages - 1;
        elements.lastPage.disabled = currentPage >= totalPages - 1;
    },
    
    showLogDetail(log) {
        // 관리자 확정 정보 렌더링
        let adminConfirmationHtml = '';
        if (log.admin_confirmed) {
            const actionLabels = {
                'immoral': { text: '비윤리', icon: 'exclamation-triangle', color: '#dc3545' },
                'spam': { text: '스팸', icon: 'envelope-open-text', color: '#ffc107' },
                'clean': { text: '문제없음', icon: 'check-circle', color: '#28a745' }
            };
            const action = actionLabels[log.confirmed_type] || { text: log.confirmed_type, icon: 'check', color: '#6c757d' };
            const confirmedAt = log.confirmed_at ? utils.formatDate(log.confirmed_at) : '-';
            
            adminConfirmationHtml = `
                <div class="detail-divider"></div>
                <div class="admin-confirmed-info" style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid ${action.color};">
                    <h4 style="margin-top: 0; color: ${action.color};">
                        <i class="fas fa-${action.icon}"></i> 관리자 확정: ${action.text}
                    </h4>
                    <div style="color: #6c757d; font-size: 0.9em; margin-top: 8px;">
                        <div><strong>확정 시간:</strong> ${confirmedAt}</div>
                        ${log.confirmed_by ? `<div><strong>확정자 ID:</strong> ${log.confirmed_by}</div>` : ''}
                    </div>
                </div>
            `;
        } else {
            // 확정되지 않은 경우만 확정 버튼 표시
            adminConfirmationHtml = `
                <div class="detail-divider"></div>
                <div class="admin-actions">
                    <h4>관리자 확정</h4>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button class="btn btn-danger" onclick="window.confirmLog(${log.id}, 'immoral')">
                            <i class="fas fa-exclamation-triangle"></i> 비윤리
                        </button>
                        <button class="btn btn-warning" onclick="window.confirmLog(${log.id}, 'spam')">
                            <i class="fas fa-envelope-open-text"></i> 스팸
                        </button>
                        <button class="btn btn-success" onclick="window.confirmLog(${log.id}, 'clean')">
                            <i class="fas fa-check-circle"></i> 문제없음
                        </button>
                    </div>
                </div>
            `;
        }
        
        elements.modalBody.innerHTML = `
            <div class="detail-row">
                <div class="detail-label">ID:</div>
                <div class="detail-value">${log.id}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">시간:</div>
                <div class="detail-value">${utils.formatDate(log.created_at)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">텍스트:</div>
                <div class="detail-value">${log.text}</div>
            </div>
            ${log.score != null ? `
            <div class="detail-row">
                <div class="detail-label">비윤리점수 (신뢰도):</div>
                <div class="detail-value">
                    <span class="${utils.getScoreClass(log.score)}">${utils.formatScore(log.score)} <small>(${utils.formatScore(log.confidence)})</small></span>
                </div>
            </div>
            ` : ''}
            ${log.spam != null ? `
            <div class="detail-row">
                <div class="detail-label">스팸지수 (신뢰도):</div>
                <div class="detail-value">
                    <span class="${utils.getSpamClass(log.spam)}">${utils.formatScore(log.spam)} <small>(${utils.formatScore(log.spam_confidence)})</small></span>
                </div>
            </div>
            ` : ''}
            <div class="detail-row">
                <div class="detail-label">유형:</div>
                <div class="detail-value">${utils.createTypeTags(log.types)}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">IP 주소:</div>
                <div class="detail-value">${log.ip_address || '-'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">User Agent:</div>
                <div class="detail-value">${log.user_agent || '-'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">응답 시간:</div>
                <div class="detail-value">${log.response_time ? log.response_time.toFixed(3) + '초' : '-'}</div>
            </div>
            <div class="detail-row">
                <div class="detail-label">RAG 보정 적용:</div>
                <div class="detail-value">
                    ${utils.createRagStatus(log.rag_applied)}
                    ${log.rag_applied && log.rag_details ? '<button class="btn-show-rag-details" onclick="var section = document.getElementById(\'rag-details-section\'); var isHidden = section.style.display === \'none\' || section.style.display === \'\'; section.style.display = isHidden ? \'block\' : \'none\'; this.innerHTML = isHidden ? \'<i class=\\\'fas fa-eye-slash\\\'></i> RAG 보정 상세정보 숨기기\' : \'<i class=\\\'fas fa-info-circle\\\'></i> RAG 보정 상세정보 보기\';" style="margin-left: 10px; padding: 4px 10px; font-size: 0.85rem; background: #3B82F6; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background=\'#2563EB\'" onmouseout="this.style.background=\'#3B82F6\'"><i class="fas fa-info-circle"></i> RAG 보정 상세정보 보기</button>' : ''}
                </div>
            </div>
            ${log.rag_details ? this.renderRagDetails(log.rag_details, log.auto_blocked) : ''}
            <div class="detail-row">
                <div class="detail-label">즉시 차단:</div>
                <div class="detail-value">${utils.createAutoBlockStatus(log.auto_blocked)}</div>
            </div>
            ${adminConfirmationHtml}
        `;
        
        elements.logModal.classList.add('show');
    },
    
    renderRagDetails(ragDetails, isAutoBlocked = false) {
        if (!ragDetails) return '';
        
        const maxSimilarity = (ragDetails.max_similarity * 100).toFixed(1);
        const adjustmentWeight = (ragDetails.adjustment_weight * 100).toFixed(1);
        const originalScore = ragDetails.original_immoral_score != null ? ragDetails.original_immoral_score.toFixed(1) : '-';
        const adjustedScore = ragDetails.adjusted_immoral_score != null ? ragDetails.adjusted_immoral_score.toFixed(1) : '-';
        const originalSpam = ragDetails.original_spam_score != null ? ragDetails.original_spam_score.toFixed(1) : '-';
        const adjustedSpam = ragDetails.adjusted_spam_score != null ? ragDetails.adjusted_spam_score.toFixed(1) : '-';
        
        // 즉시 차단 배지
        const autoBlockBadge = isAutoBlocked 
            ? '<span style="display: inline-block; background: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; margin-left: 8px;"><i class="fas fa-bolt"></i> 즉시 차단</span>'
            : '';
        
        let similarCasesHtml = '';
        if (ragDetails.similar_cases && ragDetails.similar_cases.length > 0) {
            try {
                const cases = typeof ragDetails.similar_cases === 'string' 
                    ? JSON.parse(ragDetails.similar_cases) 
                    : ragDetails.similar_cases;
                
                similarCasesHtml = cases.map((c, idx) => `
                    <div style="margin: 5px 0; padding: 8px; background: #fff; border-radius: 4px;">
                        <strong>${idx + 1}.</strong> 유사도: ${(c.similarity || 0).toFixed(1)}% | 
                        비윤리: ${(c.immoral_score || 0).toFixed(1)} | 
                        스팸: ${(c.spam_score || 0).toFixed(1)} |
                        ${c.confirmed ? '<span style="color: #28a745;">✓ 확정</span>' : '<span style="color: #999;">미확정</span>'}
                        <div style="margin-top: 5px; font-size: 0.9em; color: #666;">"${c.sentence || ''}"</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('유사 케이스 파싱 오류:', e);
                similarCasesHtml = '<div style="color: #999;">유사 케이스 정보를 표시할 수 없습니다.</div>';
            }
        }
        
        const ragId = `rag-details-${Date.now()}`;
        
        return `
            <div id="rag-details-section" style="background: #eee; padding: 15px; border-radius: 8px; margin: 15px 0; display: none;">
                <h4 style="margin-top: 0; color: #495057; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
                    <span><i class="fas fa-brain"></i> RAG 보정 상세 정보${autoBlockBadge}</span>
                </h4>
                <div>
                <div class="detail-row" style="margin-top: 12px;">
                    <div class="detail-label">유사 케이스 개수:</div>
                    <div class="detail-value"><strong>${ragDetails.similar_case_count || 0}개</strong></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">최대 유사도:</div>
                    <div class="detail-value"><strong>${maxSimilarity}%</strong></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">보정 가중치:</div>
                    <div class="detail-value"><strong>${adjustmentWeight}%</strong></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">보정 방법:</div>
                    <div class="detail-value">${ragDetails.adjustment_method || 'similarity_based'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">비윤리 점수 변화:</div>
                    <div class="detail-value">
                        <span>${originalScore}</span> 
                        → 
                        <strong>${adjustedScore}</strong>
                        ${ragDetails.original_immoral_score != null && ragDetails.adjusted_immoral_score != null && Math.abs(ragDetails.adjusted_immoral_score - ragDetails.original_immoral_score) >= 0.1
                            ? `<span>
                                (${ragDetails.adjusted_immoral_score > ragDetails.original_immoral_score ? '+' : ''}${(ragDetails.adjusted_immoral_score - ragDetails.original_immoral_score).toFixed(1)})
                               </span>`
                            : ''}
                    </div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">스팸 점수 변화:</div>
                    <div class="detail-value">
                        <span>${originalSpam}</span> 
                        → 
                        <strong>${adjustedSpam}</strong>
                        ${ragDetails.original_spam_score != null && ragDetails.adjusted_spam_score != null && Math.abs(ragDetails.adjusted_spam_score - ragDetails.original_spam_score) >= 0.1
                            ? `<span>
                                (${ragDetails.adjusted_spam_score > ragDetails.original_spam_score ? '+' : ''}${(ragDetails.adjusted_spam_score - ragDetails.original_spam_score).toFixed(1)})
                               </span>`
                            : ''}
                    </div>
                </div>
                ${ragDetails.rag_response_time ? `
                <div class="detail-row">
                    <div class="detail-label">RAG 처리 시간:</div>
                    <div class="detail-value">${ragDetails.rag_response_time.toFixed(3)}초</div>
                </div>
                ` : ''}
                ${similarCasesHtml ? `
                <div class="detail-row" style="display: block;">
                    <div class="detail-label" style="margin-bottom: 10px;">검색된 유사 케이스:</div>
                    <div style="max-height: 300px; overflow-y: auto;">
                        ${similarCasesHtml}
                    </div>
                </div>
                ` : ''}
                </div>
            </div>
            <div class="detail-divider"></div>
        `;
    },
    
    showError(message) {
        alert(`오류: ${message}`);
    }
};

// 필터 관리
const filterManager = {
    async applyFilters() {
        currentFilters = {};
        currentPage = 0;
        
        // 기간 필터 - 전체가 아닐 때만 적용
        const days = parseInt(elements.dateFilter.value);
        if (days && days > 0) {
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(endDate.getDate() - days);
            
            currentFilters.start_date = startDate.toISOString().split('T')[0];
            currentFilters.end_date = endDate.toISOString().split('T')[0];
        }
        
        await dataLoader.loadStats();
        await dataLoader.loadLogs();
        this.applyClientFilters();
    },
    
    applyClientFilters() {
        let tempFilteredLogs = [...originalLogs];
        
        // 비윤리점수 필터 (클라이언트 사이드)
        const scoreFilter = elements.scoreFilter.value;
        if (scoreFilter) {
            const [min, max] = scoreFilter.split('-').map(Number);
            tempFilteredLogs = tempFilteredLogs.filter(log => {
                const score = parseFloat(log.score);
                return score >= min && score <= max;
            });
        }
        
        // 스팸지수 필터 (클라이언트 사이드)
        const spamFilter = elements.spamFilter.value;
        if (spamFilter) {
            const [min, max] = spamFilter.split('-').map(Number);
            tempFilteredLogs = tempFilteredLogs.filter(log => {
                const spam = parseFloat(log.spam);
                return spam >= min && spam <= max;
            });
        }
        
        // 검색 필터 (클라이언트 사이드)
        const searchTerm = elements.searchInput.value.toLowerCase().trim();
        if (searchTerm) {
            tempFilteredLogs = tempFilteredLogs.filter(log => 
                log.text.toLowerCase().includes(searchTerm) ||
                (log.types && log.types.some(type => type.toLowerCase().includes(searchTerm))) ||
                (log.ip_address && log.ip_address.toLowerCase().includes(searchTerm))
            );
        }
        
        // 전역 filteredLogs 업데이트
        filteredLogs = tempFilteredLogs;
        
        // 페이지네이션 적용 - 현재 페이지의 데이터만 표시
        const startIndex = currentPage * currentLimit;
        const endIndex = startIndex + currentLimit;
        allLogs = filteredLogs.slice(startIndex, endIndex);
        
        dataLoader.renderLogs();
        dataLoader.updatePagination(filteredLogs.length);
    },
    
    clearFilters() {
        elements.scoreFilter.value = '';
        elements.spamFilter.value = '';
        elements.dateFilter.value = '';
        elements.searchInput.value = '';
        currentFilters = {};
        currentPage = 0;
        dataLoader.loadLogs();
    }
};

// 삭제 관리
const deleteManager = {
    currentLogId: null,
    
    showDeleteModal(logId, text, score) {
        this.currentLogId = logId;
        
        document.getElementById('deleteLogId').textContent = logId;
        document.getElementById('deleteLogText').textContent = utils.truncateText(text, 50);
        document.getElementById('deleteLogScore').textContent = utils.formatScore(score);
        
        elements.deleteModal.classList.add('show');
    },
    
    hideDeleteModal() {
        elements.deleteModal.classList.remove('show');
        this.currentLogId = null;
    },
    
    async confirmDelete() {
        if (!this.currentLogId) return;
        
        try {
            utils.showLoading();
            await api.deleteLog(this.currentLogId);
            
            await dataLoader.loadLogs();
            await dataLoader.loadStats();
            
            this.hideDeleteModal();
            this.showSuccessMessage('로그가 성공적으로 삭제되었습니다.');
            
        } catch (error) {
            console.error('Delete failed:', error);
            this.showErrorMessage('로그 삭제에 실패했습니다: ' + error.message);
        } finally {
            utils.hideLoading();
        }
    },
    
    showSuccessMessage(message) {
        this.showMessage(message, '#27ae60');
    },
    
    showErrorMessage(message) {
        this.showMessage(message, '#e74c3c');
    },
    
    showMessage(message, color) {
        const div = document.createElement('div');
        div.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${color};
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            animation: slideInRight 0.3s ease-out;
        `;
        div.textContent = message;
        
        document.body.appendChild(div);
        
        setTimeout(() => {
            div.remove();
        }, 3000);
    }
};

// 오래된 로그 삭제
const oldLogsManager = {
    showDeleteOldModal() {
        elements.deleteOldModal.classList.add('show');
        elements.deleteDays.value = '30';
        elements.previewCount.textContent = '-';
        
        // 모달이 열리면 자동으로 미리보기 실행
        setTimeout(() => {
            this.previewDeleteCount();
        }, 100);
    },
    
    hideDeleteOldModal() {
        elements.deleteOldModal.classList.remove('show');
    },
    
    async previewDeleteCount() {
        const days = parseInt(elements.deleteDays.value);
        
        try {
            // 로딩 표시 없이 빠르게 계산
            
            if (days === 0) {
                // 모든 로그 삭제
                const totalStats = await api.getStats(365); // 전체 통계
                elements.previewCount.textContent = totalStats.total_count || 0;
            } else {
                // N일 이전 로그 삭제 = 전체 - 최근 N일
                const totalStats = await api.getStats(365); // 전체
                const recentStats = await api.getStats(days); // 최근 N일
                
                const totalCount = totalStats.total_count || 0;
                const recentCount = recentStats.total_count || 0;
                const oldCount = Math.max(0, totalCount - recentCount);
                
                elements.previewCount.textContent = oldCount;
            }
            
        } catch (error) {
            console.error('Preview failed:', error);
            elements.previewCount.textContent = '계산 실패';
        }
    },
    
    async confirmDeleteOld() {
        const days = parseInt(elements.deleteDays.value);
        const previewCount = elements.previewCount.textContent;
        
        // 확인 메시지
        const message = days === 0 
            ? `정말로 모든 로그(약 ${previewCount}개)를 삭제하시겠습니까?`
            : `정말로 ${days}일 이전 로그(약 ${previewCount}개)를 삭제하시겠습니까?`;
        
        if (!confirm(message)) {
            return;
        }
        
        try {
            utils.showLoading();
            const result = await api.deleteOldLogs(days);
            
            await dataLoader.loadLogs();
            await dataLoader.loadStats();
            
            this.hideDeleteOldModal();
            deleteManager.showSuccessMessage(`${result.deleted_count}개의 로그가 삭제되었습니다.`);
            
        } catch (error) {
            console.error('Old logs delete failed:', error);
            deleteManager.showErrorMessage('로그 삭제에 실패했습니다: ' + error.message);
        } finally {
            utils.hideLoading();
        }
    }
};

// 페이지네이션
const pagination = {
    firstPage() {
        if (currentPage !== 0) {
            currentPage = 0;
            filterManager.applyClientFilters();
        }
    },
    
    prevPage() {
        if (currentPage > 0) {
            currentPage--;
            filterManager.applyClientFilters();
        }
    },
    
    nextPage() {
        const totalPages = Math.ceil(filteredLogs.length / currentLimit);
        if (currentPage < totalPages - 1) {
            currentPage++;
            filterManager.applyClientFilters();
        }
    },
    
    lastPage() {
        const totalPages = Math.ceil(filteredLogs.length / currentLimit);
        if (currentPage !== totalPages - 1) {
            currentPage = totalPages - 1;
            filterManager.applyClientFilters();
        }
    },
    
    changePageSize() {
        const newSize = parseInt(elements.pageSizeSelect.value);
        if (newSize !== currentLimit) {
            currentLimit = newSize;
            currentPage = 0; // 첫 페이지로 리셋
            filterManager.applyClientFilters();
        }
    }
};

// 이벤트 리스너
const eventListeners = {
    init() {
        elements.refreshBtn.addEventListener('click', () => {
            dataLoader.loadStats();
            dataLoader.loadLogs();
        });
        
        elements.applyFilters.addEventListener('click', () => {
            filterManager.applyFilters();
        });
        
        elements.clearFilters.addEventListener('click', () => {
            filterManager.clearFilters();
        });
        
        elements.searchInput.addEventListener('input', () => {
            filterManager.applyClientFilters();
        });
        
        elements.scoreFilter.addEventListener('change', () => {
            filterManager.applyClientFilters();
        });
        
        elements.spamFilter.addEventListener('change', () => {
            filterManager.applyClientFilters();
        });
        
        elements.dateFilter.addEventListener('change', () => {
            filterManager.applyFilters();
        });
        
        elements.firstPage.addEventListener('click', () => pagination.firstPage());
        elements.prevPage.addEventListener('click', () => pagination.prevPage());
        elements.nextPage.addEventListener('click', () => pagination.nextPage());
        elements.lastPage.addEventListener('click', () => pagination.lastPage());
        elements.pageSizeSelect.addEventListener('change', () => pagination.changePageSize());
        
        elements.closeModal.addEventListener('click', () => {
            elements.logModal.classList.remove('show');
        });
        
        elements.logModal.addEventListener('click', (e) => {
            if (e.target === elements.logModal) {
                elements.logModal.classList.remove('show');
            }
        });
        
        elements.closeDeleteModal.addEventListener('click', () => {
            deleteManager.hideDeleteModal();
        });
        
        elements.cancelDelete.addEventListener('click', () => {
            deleteManager.hideDeleteModal();
        });
        
        elements.confirmDelete.addEventListener('click', () => {
            deleteManager.confirmDelete();
        });
        
        elements.deleteModal.addEventListener('click', (e) => {
            if (e.target === elements.deleteModal) {
                deleteManager.hideDeleteModal();
            }
        });
        
        elements.deleteOldBtn.addEventListener('click', () => {
            oldLogsManager.showDeleteOldModal();
        });
        
        elements.closeDeleteOldModal.addEventListener('click', () => {
            oldLogsManager.hideDeleteOldModal();
        });
        
        elements.cancelDeleteOld.addEventListener('click', () => {
            oldLogsManager.hideDeleteOldModal();
        });
        
        elements.deleteDays.addEventListener('change', () => {
            oldLogsManager.previewDeleteCount();
        });
        
        elements.confirmDeleteOld.addEventListener('click', () => {
            oldLogsManager.confirmDeleteOld();
        });
        
        elements.deleteOldModal.addEventListener('click', (e) => {
            if (e.target === elements.deleteOldModal) {
                oldLogsManager.hideDeleteOldModal();
            }
        });

        if (elements.ragAllCasesCard) {
            elements.ragAllCasesCard.addEventListener('click', () => {
                allCasesModal.open();
            });
        }

        if (elements.ragConfirmedCard) {
            elements.ragConfirmedCard.addEventListener('click', () => {
                confirmedFeedbackModal.open();
            });
        }

        if (elements.autoBlockedCard) {
            elements.autoBlockedCard.addEventListener('click', () => {
                autoBlockedModal.open();
            });
        }

        if (elements.closeAllCasesModal) {
            elements.closeAllCasesModal.addEventListener('click', () => {
                allCasesModal.close();
            });
        }

        if (elements.allCasesModal) {
            elements.allCasesModal.addEventListener('click', (e) => {
                if (e.target === elements.allCasesModal) {
                    allCasesModal.close();
                }
            });
        }

        if (elements.closeFeedbackModal) {
            elements.closeFeedbackModal.addEventListener('click', () => {
                confirmedFeedbackModal.close();
            });
        }

        if (elements.feedbackModal) {
            elements.feedbackModal.addEventListener('click', (e) => {
                if (e.target === elements.feedbackModal) {
                    confirmedFeedbackModal.close();
                }
            });
        }

        if (elements.closeAutoBlockedModal) {
            elements.closeAutoBlockedModal.addEventListener('click', () => {
                autoBlockedModal.close();
            });
        }

        if (elements.autoBlockedModal) {
            elements.autoBlockedModal.addEventListener('click', (e) => {
                if (e.target === elements.autoBlockedModal) {
                    autoBlockedModal.close();
                }
            });
        }
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (elements.logModal.classList.contains('show')) {
                    elements.logModal.classList.remove('show');
                } else if (elements.deleteModal.classList.contains('show')) {
                    deleteManager.hideDeleteModal();
                } else if (elements.deleteOldModal.classList.contains('show')) {
                    oldLogsManager.hideDeleteOldModal();
                } else if (elements.allCasesModal && elements.allCasesModal.classList.contains('show')) {
                    allCasesModal.close();
                } else if (elements.feedbackModal && elements.feedbackModal.classList.contains('show')) {
                    confirmedFeedbackModal.close();
                } else if (elements.autoBlockedModal && elements.autoBlockedModal.classList.contains('show')) {
                    autoBlockedModal.close();
                }
            }
        });
    }
};

// 벡터DB 전체 사례 모달 관리
const allCasesModal = {
    isLoading: false,
    currentCases: [],
    
    open() {
        if (!elements.allCasesModal) return;
        elements.allCasesModal.classList.add('show');
        this.load();
    },
    
    close() {
        if (!elements.allCasesModal) return;
        elements.allCasesModal.classList.remove('show');
    },
    
    setBody(html) {
        if (!elements.allCasesModalBody) return;
        elements.allCasesModalBody.innerHTML = html;
    },
    
    async load() {
        if (this.isLoading) return;
        this.isLoading = true;
        
        this.setBody(`
            <div style="text-align: center; padding: 40px; color: #6B7280;">
                <i class="fas fa-spinner fa-spin" style="font-size: 28px;"></i>
                <p style="margin-top: 12px;">사례를 불러오는 중입니다...</p>
            </div>
        `);
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/admin/ethics/all-cases?limit=100`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.status === 403) {
                this.setBody(`
                    <div style="text-align: center; padding: 40px; color: #EF4444;">
                        <i class="fas fa-lock" style="font-size: 28px;"></i>
                        <p style="margin-top: 12px;">관리자 권한이 필요합니다.</p>
                    </div>
                `);
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.currentCases = data.cases || [];
            this.render();
        } catch (error) {
            console.error('Failed to load all cases:', error);
            this.setBody(`
                <div style="text-align: center; padding: 40px; color: #EF4444;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 28px;"></i>
                    <p style="margin-top: 12px;">사례를 불러오는데 실패했습니다.</p>
                    <button onclick="allCasesModal.load()" style="margin-top: 16px; padding: 8px 16px; background: #3B82F6; color: white; border: none; border-radius: 6px; cursor: pointer;">
                        <i class="fas fa-redo"></i> 다시 시도
                    </button>
                </div>
            `);
        } finally {
            this.isLoading = false;
        }
    },
    
    render() {
        if (!this.currentCases || this.currentCases.length === 0) {
            this.setBody(`
                <div style="text-align: center; padding: 40px; color: #6B7280;">
                    <i class="fas fa-inbox" style="font-size: 28px;"></i>
                    <p style="margin-top: 12px;">저장된 사례가 없습니다.</p>
                </div>
            `);
            return;
        }
        
        const itemsHtml = this.currentCases.map(item => this.buildItem(item)).join('');
        this.setBody(`
            <div style="margin-bottom: 15px; padding: 12px; background: #EFF6FF; border-radius: 8px; border-left: 4px solid #3B82F6;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-info-circle" style="color: #3B82F6;"></i>
                    <span style="color: #1E40AF; font-size: 0.95rem;">
                        RAG 시스템에서 활용하는 비윤리/스팸 케이스가 저장된 벡터 데이터베이스입니다. <br>
                        관리자 확정 및 신뢰도 80.0이상 케이스가 자동으로 저장됩니다. <br>
                        (의미있는 패턴학습을 위해 10자 이상 텍스트만 저장합니다.)
                    </span>
                </div>
            </div>
            <div class="feedback-list feedback-items-container">
                ${itemsHtml}
            </div>
        `);
        
        this.attachDeleteHandlers();
    },
    
    buildItem(item) {
        const metadata = item.metadata || {};
        const confirmed = item.confirmed || metadata.confirmed || false;
        
        // 확정 상태 배지 생성
        let statusBadges = '';
        if (confirmed) {
            // 확정된 경우: "확정" 배지 + admin_action 배지
            statusBadges = '<span class="feedback-badge feedback-clean" style="font-size: 0.85rem; padding: 4px 12px;"><i class="fas fa-check-circle"></i> 확정</span>';
            
            // admin_action이 있으면 추가 배지 표시
            let action = metadata.admin_action || item.admin_action;
            if (typeof action === 'string') {
                action = action.toLowerCase();
            }
            
            // admin_action이 없으면 점수로 유추
            if (!action || action === '') {
                const immoralScore = parseFloat(item.immoral_score ?? metadata.immoral_score ?? 0);
                const spamScore = parseFloat(item.spam_score ?? metadata.spam_score ?? 0);
                
                if (immoralScore >= 80) {
                    action = 'immoral';
                } else if (spamScore >= 80) {
                    action = 'spam';
                } else if (immoralScore <= 20 && spamScore <= 20) {
                    action = 'clean';
                }
            }
            
            // admin_action 배지 추가 (동일한 사이즈로)
            if (action && action !== '') {
                const actionLabel = {
                    'immoral': '비윤리',
                    'spam': '스팸',
                    'clean': '문제없음'
                }[action] || action;
                const actionClass = {
                    'immoral': 'feedback-immoral',
                    'spam': 'feedback-spam',
                    'clean': 'feedback-clean'
                }[action] || 'feedback-none';
                statusBadges += ` <span class="feedback-badge ${actionClass}" style="font-size: 0.85rem; padding: 4px 12px;">${actionLabel}</span>`;
            }
        } else {
            // 미확정인 경우
            statusBadges = '<span class="feedback-badge feedback-none" style="font-size: 0.85rem; padding: 4px 12px;"><i class="fas fa-clock"></i> 미확정</span>';
        }

        const createdRaw = item.created_at || metadata.created_at;
        const createdAt = createdRaw ? utils.formatDate(createdRaw) : '-';

        const userId = metadata.user_id || item.user_id || '-';
        const postId = metadata.post_id || item.post_id || '-';

        const contentSource = item.text || metadata.sentence;
        const contentText = contentSource
            ? utils.escapeHtml(contentSource).replace(/\n/g, '<br>')
            : '<em>내용을 찾을 수 없습니다.</em>';

        const immoralScore = utils.formatScore(item.immoral_score ?? metadata.immoral_score);
        const spamScore = utils.formatScore(item.spam_score ?? metadata.spam_score);
        const immoralConfidence = utils.formatScore(item.immoral_confidence ?? metadata.immoral_confidence ?? 0);
        const spamConfidence = utils.formatScore(item.spam_confidence ?? metadata.spam_confidence ?? 0);

        const feedbackType = metadata.feedback_type || '-';
        const adminAction = metadata.admin_action || '-';

        return `
            <div class="feedback-item">
                <div class="feedback-item-header">
                    ${statusBadges}
                    <span style="font-size: 0.9rem; color: #6B7280;">
                        ${createdAt}
                    </span>
                    <button class="feedback-delete-btn" data-case-id="${item.id}" title="삭제">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
                <div class="feedback-item-meta">
                    <span class="feedback-info-chip"><i class="fas fa-user"></i> ${utils.escapeHtml(userId)}</span>
                    <span class="feedback-info-chip"><i class="fas fa-link"></i> ${utils.escapeHtml(postId)}</span>
                    <span class="feedback-info-chip"><i class="fas fa-bookmark"></i> ${utils.escapeHtml(feedbackType)}</span>
                    ${adminAction !== '-' ? `<span class="feedback-info-chip"><i class="fas fa-gavel"></i> ${utils.escapeHtml(adminAction)}</span>` : ''}
                </div>
                <div class="feedback-item-content">${contentText}</div>
                <div class="feedback-item-meta" style="margin-top: 6px;">
                    <span class="feedback-score-chip feedback-score-immoral"><i class="fas fa-bolt"></i> 비윤리 ${immoralScore}</span>
                    <span class="feedback-score-chip feedback-score-confidence"><i class="fas fa-shield-alt"></i> 비윤리 신뢰도 ${immoralConfidence}</span>
                    <span class="feedback-score-chip feedback-score-spam"><i class="fas fa-envelope"></i> 스팸 ${spamScore}</span>
                    <span class="feedback-score-chip feedback-score-confidence"><i class="fas fa-shield-alt"></i> 스팸 신뢰도 ${spamConfidence}</span>
                </div>
            </div>
        `;
    },
    
    attachDeleteHandlers() {
        const deleteButtons = elements.allCasesModalBody.querySelectorAll('.feedback-delete-btn');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const caseId = btn.getAttribute('data-case-id');
                if (!caseId) return;

                if (!confirm('이 사례를 삭제하시겠습니까?')) return;

                try {
                    await this.deleteCase(caseId);
                    alert('사례가 삭제되었습니다.');
                    this.load();
                    await dataLoader.loadStats();
                } catch (error) {
                    console.error('Delete failed:', error);
                    alert('삭제 중 오류가 발생했습니다.');
                }
            });
        });
    },
    
    async deleteCase(caseId) {
        const response = await fetch(`${API_BASE_URL}/api/admin/ethics/feedback/${caseId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }
};

const confirmedFeedbackModal = {
    isLoading: false,
    currentFeedbacks: [],
    
    open() {
        if (!elements.feedbackModal) return;
        elements.feedbackModal.classList.add('show');
        this.load();
    },
    
    close() {
        if (!elements.feedbackModal) return;
        elements.feedbackModal.classList.remove('show');
    },
    
    setBody(html) {
        if (!elements.feedbackModalBody) return;
        elements.feedbackModalBody.innerHTML = html;
    },
    
    async load() {
        if (this.isLoading) return;
        this.isLoading = true;
        this.setBody(`
            <div style="text-align: center; padding: 40px; color: #6B7280;">
                <i class="fas fa-spinner fa-spin" style="font-size: 28px;"></i>
                <p style="margin-top: 12px;">확정 사례를 불러오는 중입니다...</p>
            </div>
        `);
        
        try {
            const response = await api.getConfirmedFeedbacks({ limit: 50 });
            const feedbacks = response.feedbacks || [];
            this.currentFeedbacks = feedbacks;
            this.render(feedbacks);
        } catch (error) {
            console.error('Failed to load confirmed feedbacks:', error);
            
            // 403 에러인 경우 권한 메시지
            if (error.message && error.message.includes('403')) {
                this.setBody(`
                    <div class="feedback-empty">
                        <i class="fas fa-lock" style="font-size: 26px; margin-bottom: 10px; color: #ef4444;"></i>
                        <p>관리자 권한이 필요합니다.</p>
                        <p style="font-size: 0.9rem; color: #6B7280; margin-top: 8px;">관리자 계정으로 <a href="/login">로그인</a>해주세요.</p>
                    </div>
                `);
            } else {
                this.setBody(`
                    <div class="feedback-empty">
                        <i class="fas fa-exclamation-circle" style="font-size: 26px; margin-bottom: 10px;"></i>
                        <p>확정 사례를 불러오는데 실패했습니다.</p>
                    </div>
                `);
            }
        } finally {
            this.isLoading = false;
        }
    },
    
    render(feedbacks) {
        if (!feedbacks.length) {
            this.setBody(`
                <div class="feedback-empty">
                    <i class="fas fa-inbox" style="font-size: 26px; margin-bottom: 10px;"></i>
                    <p>표시할 확정 사례가 없습니다.</p>
                </div>
            `);
            return;
        }
        
        const listHtml = feedbacks.map((item) => this.buildItem(item)).join('');
        this.setBody(`
            <div style="margin-bottom: 15px; padding: 12px; background: #EFF6FF; border-radius: 8px; border-left: 4px solid #3B82F6;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <i class="fas fa-info-circle" style="color: #3B82F6;"></i>
                    <span style="color: #1E40AF; font-size: 0.95rem;">
                        관리자가 로그 또는 신고 내용을 검토하여 비윤리/스팸/문제없음으로 확정한 사례입니다. <br>
                        확정된 사례는 벡터DB에 저장되어 RAG 시스템의 학습 데이터로 활용됩니다.
                    </span>
                </div>
            </div>
            <div class="feedback-list">${listHtml}</div>
        `);
        this.attachDeleteHandlers();
    },
    
    attachDeleteHandlers() {
        const deleteButtons = elements.feedbackModalBody.querySelectorAll('.feedback-delete-btn');
        deleteButtons.forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const caseId = btn.getAttribute('data-case-id');
                if (!caseId) return;
                
                if (!confirm('이 확정 사례를 삭제하시겠습니까?')) {
                    return;
                }
                
                btn.disabled = true;
                try {
                    await this.deleteCase(caseId);
                    this.currentFeedbacks = this.currentFeedbacks.filter(item => item.id !== caseId);
                    this.render(this.currentFeedbacks);
                    alert('삭제되었습니다.');
                } catch (error) {
                    console.error('삭제 실패:', error);
                    alert('삭제 중 오류가 발생했습니다.');
                    btn.disabled = false;
                }
            });
        });
    },
    
    async deleteCase(caseId) {
        const response = await fetch(`${API_BASE_URL}/api/admin/ethics/feedback/${caseId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    },
    
    buildItem(item) {
        const metadata = item.metadata || {};
        let action = item.admin_action || metadata.admin_action;
        if (typeof action === 'string') {
            action = action.toLowerCase();
        } else {
            action = '';
        }
        
        // action이 비어있으면 점수로 유추
        if (!action || action === '') {
            const immoralScore = parseFloat(item.immoral_score ?? metadata.immoral_score ?? 0);
            const spamScore = parseFloat(item.spam_score ?? metadata.spam_score ?? 0);
            
            if (immoralScore >= 80) {
                action = 'immoral';
            } else if (spamScore >= 80) {
                action = 'spam';
            } else if (immoralScore <= 20 && spamScore <= 20) {
                action = 'clean';
            }
        }
        
        const actionBadge = utils.createFeedbackBadge(action);
        const createdRaw = item.created_at || metadata.created_at;
        const createdAt = createdRaw ? utils.formatDate(createdRaw) : '-';

        const adminId = metadata.admin_id || item.admin_id;
        const adminLabel = adminId ? `관리자 ID ${adminId}` : '관리자';

        const sourceType = item.source_type || metadata.source_type || 'ethics_log';
        const sourceLabel = this.getSourceLabel(sourceType);

        const contentSource = item.text || metadata.sentence;
        const contentText = contentSource
            ? utils.escapeHtml(contentSource).replace(/\n/g, '<br>')
            : '<em>내용을 찾을 수 없습니다.</em>';

        const noteValue = item.note ?? metadata.note;
        const noteHtml = noteValue ? `
            <div class="feedback-item-note">
                <i class="fas fa-sticky-note"></i> ${utils.escapeHtml(noteValue).replace(/\n/g, '<br>')}
            </div>
        ` : '';

        const immoralScore = utils.formatScore(item.immoral_score ?? metadata.immoral_score);
        const spamScore = utils.formatScore(item.spam_score ?? metadata.spam_score);
        const immoralConfidence = utils.formatScore(item.immoral_confidence ?? metadata.immoral_confidence ?? 0);
        const spamConfidence = utils.formatScore(item.spam_confidence ?? metadata.spam_confidence ?? 0);

        const infoChips = [
            metadata.feedback_type ? `<span class="feedback-info-chip"><i class="fas fa-bookmark"></i> ${utils.escapeHtml(metadata.feedback_type)}</span>` : '',
            sourceType === 'report' && (metadata.report_id || metadata.source_id)
                ? `<span class="feedback-info-chip"><i class="fas fa-flag"></i> 신고 ID ${metadata.report_id || metadata.source_id}</span>`
                : '',
            metadata.post_id
                ? `<span class="feedback-info-chip"><i class="fas fa-link"></i> ${utils.escapeHtml(metadata.post_id)}</span>`
                : ''
        ].filter(Boolean).join('');

        const scoreMeta = `
            <div class="feedback-item-meta" style="margin-top: 6px;">
                <span class="feedback-score-chip feedback-score-immoral"><i class="fas fa-bolt"></i> 비윤리 ${immoralScore}</span>
                <span class="feedback-score-chip feedback-score-confidence"><i class="fas fa-shield-alt"></i> 비윤리 신뢰도 ${immoralConfidence}</span>
                <span class="feedback-score-chip feedback-score-spam"><i class="fas fa-envelope"></i> 스팸 ${spamScore}</span>
                <span class="feedback-score-chip feedback-score-confidence"><i class="fas fa-shield-alt"></i> 스팸 신뢰도 ${spamConfidence}</span>
            </div>
        `;

        const extraMeta = infoChips
            ? `<div class="feedback-item-meta">${infoChips}</div>`
            : '';

        return `
            <div class="feedback-item">
                <div class="feedback-item-header">
                    ${actionBadge}
                    <span style="font-size: 0.9rem; color: #6B7280;">
                        ${createdAt}
                    </span>
                    <button class="feedback-delete-btn" data-case-id="${item.id}" title="삭제">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
                <div class="feedback-item-meta">
                    <span class="feedback-info-chip"><i class="fas fa-user-shield"></i> ${adminLabel}</span>
                    <span class="feedback-info-chip"><i class="fas fa-folder-open"></i> ${sourceLabel}</span>
                </div>
                ${extraMeta}
                <div class="feedback-item-content">${contentText}</div>
                ${noteHtml}
                ${scoreMeta}
            </div>
        `;
    },
    
    getSourceLabel(sourceType) {
        switch (sourceType) {
            case 'report':
                return '신고 확정';
            case 'ethics_log':
            default:
                return '윤리 로그 확정';
        }
    }
};

// 즉시 차단 사례 모달 관리
const autoBlockedModal = {
    isLoading: false,
    currentLogs: [],
    
    open() {
        if (!elements.autoBlockedModal) return;
        elements.autoBlockedModal.classList.add('show');
        this.load();
    },
    
    close() {
        if (!elements.autoBlockedModal) return;
        elements.autoBlockedModal.classList.remove('show');
    },
    
    setBody(html) {
        const modalBody = document.getElementById('autoBlockedModalBody');
        if (!modalBody) return;
        modalBody.innerHTML = html;
    },
    
    async load() {
        if (this.isLoading) return;
        this.isLoading = true;
        
        this.setBody(`
            <div style="text-align: center; padding: 40px; color: #6B7280;">
                <i class="fas fa-spinner fa-spin" style="font-size: 28px;"></i>
                <p style="margin-top: 12px;">즉시 차단 사례를 불러오는 중입니다...</p>
            </div>
        `);
        
        try {
            // auto_blocked = 1인 로그들만 조회
            const response = await fetch(`${API_BASE_URL}/api/ethics/logs?limit=100`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            const logs = data.logs || [];
            
            // auto_blocked = 1인 항목만 필터링
            const autoBlockedLogs = logs.filter(log => log.auto_blocked === 1 || log.auto_blocked === true);
            
            this.currentLogs = autoBlockedLogs;
            this.render(autoBlockedLogs);
        } catch (error) {
            console.error('Failed to load auto blocked logs:', error);
            this.setBody(`
                <div style="text-align: center; padding: 40px; color: #EF4444;">
                    <i class="fas fa-exclamation-circle" style="font-size: 28px;"></i>
                    <p style="margin-top: 12px;">사례를 불러오는 중 오류가 발생했습니다.</p>
                    <p style="font-size: 0.9rem; color: #6B7280; margin-top: 8px;">${error.message}</p>
                </div>
            `);
        } finally {
            this.isLoading = false;
        }
    },
    
    render(logs) {
        if (!logs || logs.length === 0) {
            this.setBody(`
                <div style="text-align: center; padding: 40px; color: #6B7280;">
                    <i class="fas fa-inbox" style="font-size: 28px; opacity: 0.5;"></i>
                    <p style="margin-top: 12px;">즉시 차단된 사례가 없습니다.</p>
                </div>
            `);
            return;
        }
        
        const logsHtml = logs.map(log => this.renderLogItem(log)).join('');
        
        this.setBody(`
            <div style="margin-bottom: 15px; padding: 12px; background: #EFF6FF; border-radius: 8px; border-left: 4px solid #3B82F6;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-info-circle" style="color: #3B82F6;"></i>
                    <span style="color: #1E40AF; font-size: 0.95rem;">
                        벡터DB에 저장된 관리자 확정 케이스와 90% 이상 유사도를 보이며, 비윤리 또는 스팸 점수 90점 이상, 신뢰도 80 이상인 경우 즉시 차단 됩니다.
                        비용과 시간이 많이 소요되는 LLM 분석을 건너뛰고, 과거 확정 판단을 기반으로 빠르게 처리합니다. <br>
                        <strong>※ 즉시 차단된 케이스는 벡터DB에 중복 저장되지 않습니다.</strong>
                    </span>
                </div>
            </div>
            <div class="feedback-list">
                ${logsHtml}
            </div>
        `);
    },
    
    renderLogItem(log) {
        const createdAt = utils.formatDate(log.created_at);
        const contentText = utils.escapeHtml(log.text || '내용 없음');
        const immoralScore = (log.score || 0).toFixed(1);
        const spamScore = (log.spam || 0).toFixed(1);
        const confidence = (log.confidence || 0).toFixed(1);
        
        // RAG 상세 정보가 있는지 확인
        const ragDetails = log.rag_details;
        let ragInfoHtml = '';
        if (ragDetails && ragDetails.max_similarity) {
            const similarity = (ragDetails.max_similarity * 100).toFixed(1);
            ragInfoHtml = `
                <div class="feedback-item-meta" style="margin-top: 8px;">
                    <span class="feedback-info-chip" style="background: #DBEAFE; color: #1E40AF;">
                        <i class="fas fa-chart-line"></i> 최대 유사도: ${similarity}%
                    </span>
                    <span class="feedback-info-chip" style="background: #FEF3C7; color: #92400E;">
                        <i class="fas fa-database"></i> 유사 케이스: ${ragDetails.similar_case_count || 0}개
                    </span>
                </div>
            `;
        }
        
        return `
            <div class="feedback-item">
                <div class="feedback-item-header">
                    <span class="feedback-action-badge" style="background: #FEE2E2; color: #991B1B;">
                        <i class="fas fa-ban"></i> 즉시 차단
                    </span>
                    <span style="font-size: 0.9rem; color: #6B7280;">
                        ${createdAt}
                    </span>
                </div>
                ${ragInfoHtml}
                <div class="feedback-item-content">${contentText}</div>
                <div class="feedback-item-meta" style="margin-top: 6px;">
                    <span class="feedback-score-chip feedback-score-immoral">
                        <i class="fas fa-bolt"></i> 비윤리 ${immoralScore}
                    </span>
                    <span class="feedback-score-chip feedback-score-confidence">
                        <i class="fas fa-shield-alt"></i> 신뢰도 ${confidence}
                    </span>
                    <span class="feedback-score-chip feedback-score-spam">
                        <i class="fas fa-envelope"></i> 스팸 ${spamScore}
                    </span>
                </div>
            </div>
        `;
    }
};

// 관리자 확정 함수 (전역)
window.confirmLog = async function(logId, action) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/ethics/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                log_id: logId,
                action: action,
                note: null
            })
        });

        if (response.status === 403) {
            alert('관리자 권한이 필요합니다. 관리자 계정으로 로그인해주세요.');
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        const actionLabel = {
            'immoral': '비윤리',
            'spam': '스팸',
            'clean': '문제없음'
        }[action] || action;
        alert(`확정되었습니다: ${actionLabel}`);
        
        // 모달 닫기
        elements.logModal.classList.remove('show');
        
        // 통계와 로그 목록 새로고침
        await dataLoader.loadStats();
        await dataLoader.loadLogs();
    } catch (error) {
        console.error('확정 실패:', error);
        if (error.message.includes('관리자 권한')) {
            alert(error.message);
        } else {
            alert('확정 중 오류가 발생했습니다. 다시 시도해주세요.');
        }
    }
};

// ============================================
// 이미지 분석 관련 함수
// ============================================

const imageAnalysis = {
    currentPage: 1,
    currentLimit: 20,
    blockedFilter: '',
    
    // 이미지 분석 통계 로드
    async loadImageStats() {
        try {
            const response = await fetch('/api/admin/images/stats');
            if (!response.ok) throw new Error('통계 로드 실패');
            
            const data = await response.json();
            const stats = data.total_stats;
            
            // 통계 업데이트
            document.getElementById('imageAnalyzedCount').textContent = stats.total_analyzed || 0;
            document.getElementById('imageBlockedCount').textContent = stats.total_blocked || 0;
            document.getElementById('imageNsfwCount').textContent = stats.total_nsfw || 0;
            
            const avgTime = stats.avg_response_time != null ? `${stats.avg_response_time.toFixed(2)}초` : '-';
            document.getElementById('imageAvgResponseTime').textContent = avgTime;
            
            const avgImmoral = stats.avg_immoral_score != null ? stats.avg_immoral_score.toFixed(1) : '-';
            const avgSpam = stats.avg_spam_score != null ? stats.avg_spam_score.toFixed(1) : '-';
            const avgNsfw = stats.avg_nsfw_confidence != null ? stats.avg_nsfw_confidence.toFixed(1) : '-';
            
            document.getElementById('imageAvgImmoral').textContent = avgImmoral;
            document.getElementById('imageAvgSpam').textContent = avgSpam;
            document.getElementById('imageAvgNsfwConf').textContent = avgNsfw;
            
        } catch (error) {
            console.error('이미지 통계 로드 실패:', error);
        }
    },
    
    // 이미지 분석 로그 로드
    async loadImageLogs() {
        try {
            utils.showLoading();
            
            const params = new URLSearchParams({
                page: this.currentPage,
                limit: this.currentLimit
            });
            
            if (this.blockedFilter) {
                params.append('blocked_only', this.blockedFilter === 'true');
            }
            
            const response = await fetch(`/api/admin/images/logs?${params}`);
            if (!response.ok) throw new Error('로그 로드 실패');
            
            const data = await response.json();
            this.renderImageLogs(data.logs);
            this.updateImagePagination(data.pagination);
            
            document.getElementById('imageLogCount').textContent = 
                `${data.pagination.total}개`;
            
        } catch (error) {
            console.error('이미지 로그 로드 실패:', error);
            document.getElementById('imageLogsTableBody').innerHTML = 
                '<tr><td colspan="10" style="text-align:center; padding:40px; color:#6B7280;">로그를 불러오지 못했습니다.</td></tr>';
        } finally {
            utils.hideLoading();
        }
    },
    
    // 이미지 로그 렌더링
    renderImageLogs(logs) {
        const tbody = document.getElementById('imageLogsTableBody');
        
        if (!logs || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:40px; color:#6B7280;">로그가 없습니다.</td></tr>';
            return;
        }
        
        tbody.innerHTML = logs.map(log => {
            const nsfwBadge = log.is_nsfw 
                ? `<span class="status-badge status-nsfw">NSFW ${(log.nsfw_confidence || 0).toFixed(0)}%</span>`
                : `<span class="status-badge status-normal">정상 ${(log.nsfw_confidence || 0).toFixed(0)}%</span>`;
            
            const blockBadge = log.is_blocked
                ? `<span class="status-badge status-blocked">차단됨</span>`
                : `<span class="status-badge status-passed">통과</span>`;
            
            const getScoreClass = (score) => {
                if (!score) return 'score-low';
                if (score >= 70) return 'score-high';
                if (score >= 40) return 'score-medium';
                return 'score-low';
            };
            
            const immoralScore = log.immoral_score != null
                ? `<span class="score-cell ${getScoreClass(log.immoral_score)}">${log.immoral_score.toFixed(0)}</span>`
                : '-';
            
            const spamScore = log.spam_score != null
                ? `<span class="score-cell ${getScoreClass(log.spam_score)}">${log.spam_score.toFixed(0)}</span>`
                : '-';
            
            const boardLink = log.board_id 
                ? `<a href="/board/${log.board_id}" target="_blank">${log.board_title || `#${log.board_id}`}</a>`
                : '-';
            
            const uploader = log.uploader_name || '-';
            
            const createdAt = new Date(log.created_at).toLocaleString('ko-KR');
            
            return `
                <tr style="cursor: pointer;" onclick="imageAnalysis.viewDetail(${log.id})" title="클릭하여 상세정보 보기">
                    <td>${log.id}</td>
                    <td title="${log.filename}">${log.original_name || log.filename.substring(0, 15) + '...'}</td>
                    <td>${boardLink}</td>
                    <td>${uploader}</td>
                    <td>${nsfwBadge}</td>
                    <td>${immoralScore}</td>
                    <td>${spamScore}</td>
                    <td>${blockBadge}</td>
                    <td>${createdAt}</td>
                    <td onclick="event.stopPropagation()">
                        <button class="btn btn-sm btn-danger" onclick="imageAnalysis.deleteLog(${log.id})" title="로그 삭제">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    },
    
    // 페이지네이션 업데이트
    updateImagePagination(pagination) {
        const { page, total_pages } = pagination;
        
        document.getElementById('imagePageInfo').textContent = `${page} / ${total_pages}`;
        
        document.getElementById('imageFirstPage').disabled = page <= 1;
        document.getElementById('imagePrevPage').disabled = page <= 1;
        document.getElementById('imageNextPage').disabled = page >= total_pages;
        document.getElementById('imageLastPage').disabled = page >= total_pages;
    },
    
    // 상세 정보 보기
    async viewDetail(logId) {
        try {
            utils.showLoading();
            
            // 현재 로드된 로그에서 찾기
            const tbody = document.getElementById('imageLogsTableBody');
            const rows = tbody.querySelectorAll('tr');
            let logData = null;
            
            // API로 상세 정보 가져오기 (더 정확한 방법)
            const response = await fetch(`/api/admin/images/logs?page=1&limit=1000`);
            if (response.ok) {
                const data = await response.json();
                logData = data.logs.find(log => log.id === logId);
            }
            
            if (!logData) {
                alert('로그 정보를 찾을 수 없습니다.');
                return;
            }
            
            // 모달 내용 생성
            const modalBody = document.getElementById('imageLogModalBody');
            
            const detectedTypes = logData.detected_types ? JSON.parse(logData.detected_types) : [];
            const typesHtml = detectedTypes.length > 0 
                ? detectedTypes.map(t => `<span class="badge badge-warning">${t}</span>`).join(' ')
                : '<span class="text-muted">없음</span>';
            
            const blockReasonHtml = logData.is_blocked && logData.block_reason
                ? `<div class="alert alert-danger"><i class="fas fa-ban"></i> ${logData.block_reason}</div>`
                : '';
            
            const extractedTextHtml = logData.has_text && logData.extracted_text
                ? `<div class="detail-section">
                    <h4><i class="fas fa-text"></i> 이미지 내 추출된 텍스트</h4>
                    <div class="extracted-text-box">${logData.extracted_text}</div>
                </div>`
                : '';
            
            modalBody.innerHTML = `
                ${blockReasonHtml}
                
                <div class="detail-grid">
                    <div class="detail-row">
                        <span class="detail-label">로그 ID:</span>
                        <span class="detail-value">${logData.id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">파일명 (UUID):</span>
                        <span class="detail-value">${logData.filename}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">원본 파일명:</span>
                        <span class="detail-value">${logData.original_name || '-'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">파일 크기:</span>
                        <span class="detail-value">${logData.file_size ? (logData.file_size / 1024).toFixed(2) + ' KB' : '-'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">게시글:</span>
                        <span class="detail-value">
                            ${logData.board_id 
                                ? `<a href="/board/${logData.board_id}" target="_blank">${logData.board_title || '#' + logData.board_id}</a>` 
                                : '-'}
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">업로더:</span>
                        <span class="detail-value">${logData.uploader_name || '-'}</span>
                    </div>
                </div>
                
                <div class="detail-divider"></div>
                
                <h4><i class="fas fa-chart-bar"></i> NSFW 분석 결과 (1차 필터)</h4>
                <div class="detail-grid">
                    <div class="detail-row">
                        <span class="detail-label">NSFW 검사:</span>
                        <span class="detail-value">${logData.nsfw_checked ? '✅ 실행됨' : '❌ 미실행'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">NSFW 판정:</span>
                        <span class="detail-value">
                            ${logData.is_nsfw 
                                ? '<span class="badge badge-danger">NSFW 감지</span>' 
                                : '<span class="badge badge-success">정상</span>'}
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">NSFW 신뢰도:</span>
                        <span class="detail-value">
                            <strong style="color: ${logData.nsfw_confidence >= 80 ? '#DC2626' : logData.nsfw_confidence >= 60 ? '#F59E0B' : '#059669'}">
                                ${logData.nsfw_confidence ? logData.nsfw_confidence.toFixed(1) + '%' : '-'}
                            </strong>
                        </span>
                    </div>
                </div>
                
                <div class="detail-divider"></div>
                
                <h4><i class="fas fa-robot"></i> Vision API 분석 결과 (2차 검증)</h4>
                <div class="detail-grid">
                    <div class="detail-row">
                        <span class="detail-label">Vision 검사:</span>
                        <span class="detail-value">${logData.vision_checked ? '✅ 실행됨' : '❌ 미실행'}</span>
                    </div>
                    ${logData.vision_checked ? `
                    <div class="detail-row">
                        <span class="detail-label">비윤리 점수:</span>
                        <span class="detail-value">
                            <strong style="color: ${logData.immoral_score >= 70 ? '#DC2626' : logData.immoral_score >= 40 ? '#F59E0B' : '#059669'}">
                                ${logData.immoral_score != null ? logData.immoral_score.toFixed(1) : '-'}
                            </strong>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">스팸 점수:</span>
                        <span class="detail-value">
                            <strong style="color: ${logData.spam_score >= 70 ? '#DC2626' : logData.spam_score >= 40 ? '#F59E0B' : '#059669'}">
                                ${logData.spam_score != null ? logData.spam_score.toFixed(1) : '-'}
                            </strong>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Vision 신뢰도:</span>
                        <span class="detail-value">${logData.vision_confidence != null ? logData.vision_confidence.toFixed(1) + '%' : '-'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">감지된 유형:</span>
                        <span class="detail-value">${typesHtml}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">텍스트 포함:</span>
                        <span class="detail-value">${logData.has_text ? '✅ 예' : '❌ 아니오'}</span>
                    </div>
                    ` : ``}
                </div>
                
                ${extractedTextHtml}
                
                <div class="detail-divider"></div>
                
                <h4><i class="fas fa-info-circle"></i> 메타데이터</h4>
                <div class="detail-grid">
                    <div class="detail-row">
                        <span class="detail-label">최종 차단 여부:</span>
                        <span class="detail-value">
                            ${logData.is_blocked 
                                ? '<span class="badge badge-danger">차단됨</span>' 
                                : '<span class="badge badge-success">통과</span>'}
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">분석 소요 시간:</span>
                        <span class="detail-value">${logData.response_time ? logData.response_time.toFixed(2) + '초' : '-'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">IP 주소:</span>
                        <span class="detail-value">${logData.ip_address || '-'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">분석 일시:</span>
                        <span class="detail-value">${new Date(logData.created_at).toLocaleString('ko-KR')}</span>
                    </div>
                </div>
            `;
            
            // 모달 표시
            document.getElementById('imageLogModal').classList.add('show');
            
        } catch (error) {
            console.error('상세 정보 로드 실패:', error);
            alert('상세 정보를 불러오는 중 오류가 발생했습니다.');
        } finally {
            utils.hideLoading();
        }
    },
    
    // 페이지 이동
    goToPage(page) {
        this.currentPage = page;
        this.loadImageLogs();
    },
    
    // 필터 적용
    applyFilters() {
        this.blockedFilter = document.getElementById('imageBlockedFilter').value;
        this.currentLimit = parseInt(document.getElementById('imagePageSize').value);
        this.currentPage = 1;
        this.loadImageLogs();
    },
    
    // 로그 삭제
    async deleteLog(logId) {
        if (!confirm('이 이미지 분석 로그를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.')) {
            return;
        }
        
        try {
            utils.showLoading();
            
            const response = await fetch(`/api/admin/images/logs/${logId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '로그 삭제 실패');
            }
            
            const result = await response.json();
            alert('로그가 삭제되었습니다.');
            
            // 목록 새로고침
            await this.loadImageStats();
            await this.loadImageLogs();
            
        } catch (error) {
            console.error('로그 삭제 실패:', error);
            alert('로그 삭제 중 오류가 발생했습니다: ' + error.message);
        } finally {
            utils.hideLoading();
        }
    }
};

// 탭 전환 함수
const tabs = {
    init() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = button.dataset.tab;
                this.switchTab(tabName);
            });
        });
    },
    
    switchTab(tabName) {
        // 모든 탭 버튼에서 active 제거
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // 모든 탭 콘텐츠 숨기기
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // 선택된 탭 활성화
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}AnalysisTab`).classList.add('active');
        
        // 이미지 탭으로 전환 시 데이터 로드
        if (tabName === 'image') {
            imageAnalysis.loadImageStats();
            imageAnalysis.loadImageLogs();
        }
    }
};

// 이미지 분석 이벤트 리스너
const imageEventListeners = {
    init() {
        // 필터 적용 버튼
        document.getElementById('imageApplyFilters')?.addEventListener('click', () => {
            imageAnalysis.applyFilters();
        });
        
        // 페이지네이션
        document.getElementById('imageFirstPage')?.addEventListener('click', () => {
            imageAnalysis.goToPage(1);
        });
        
        document.getElementById('imagePrevPage')?.addEventListener('click', () => {
            imageAnalysis.goToPage(Math.max(1, imageAnalysis.currentPage - 1));
        });
        
        document.getElementById('imageNextPage')?.addEventListener('click', () => {
            imageAnalysis.goToPage(imageAnalysis.currentPage + 1);
        });
        
        document.getElementById('imageLastPage')?.addEventListener('click', () => {
            // 마지막 페이지는 로드 후 알 수 있으므로 임시로 큰 수 사용
            const totalPages = parseInt(document.getElementById('imagePageInfo').textContent.split('/')[1].trim());
            imageAnalysis.goToPage(totalPages);
        });
        
        // 이미지 로그 모달 닫기
        document.getElementById('closeImageLogModal')?.addEventListener('click', () => {
            document.getElementById('imageLogModal').classList.remove('show');
        });
        
        // 모달 배경 클릭 시 닫기
        document.getElementById('imageLogModal')?.addEventListener('click', (e) => {
            if (e.target.id === 'imageLogModal') {
                document.getElementById('imageLogModal').classList.remove('show');
            }
        });
    }
};

// refreshBtn이 이미지 탭 새로고침도 담당하도록 수정
const originalRefreshHandler = elements.refreshBtn?.onclick;
if (elements.refreshBtn) {
    elements.refreshBtn.addEventListener('click', async () => {
        // 현재 활성화된 탭 확인
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab && activeTab.id === 'imageAnalysisTab') {
            // 이미지 탭이 활성화되어 있으면
            await imageAnalysis.loadImageStats();
            await imageAnalysis.loadImageLogs();
        } else {
            // 텍스트 탭이 활성화되어 있으면 기존 동작
            await dataLoader.loadStats();
            await dataLoader.loadLogs();
        }
    });
}

// 초기화
const app = {
    async init() {
        try {
            eventListeners.init();
            tabs.init();
            imageEventListeners.init();
            await dataLoader.loadStats();
            await dataLoader.loadLogs();
        } catch (error) {
            console.error('App initialization failed:', error);
            dataLoader.showError('애플리케이션 초기화에 실패했습니다.');
        }
    }
};

    // 초기화 실행
    document.addEventListener('DOMContentLoaded', () => {
        app.init();
    });
    
    // imageAnalysis를 전역으로 노출 (버튼 onclick에서 사용)
    window.imageAnalysis = imageAnalysis;
})();

