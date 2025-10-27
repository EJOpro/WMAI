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
    previewDelete: document.getElementById('previewDelete'),
    confirmDeleteOld: document.getElementById('confirmDeleteOld'),
    cancelDeleteOld: document.getElementById('cancelDeleteOld'),
    totalCount: document.getElementById('totalCount'),
    highRiskCount: document.getElementById('highRiskCount'),
    spamCount: document.getElementById('spamCount'),
    avgScore: document.getElementById('avgScore')
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
        return parseFloat(score).toFixed(1);
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
    }
};

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
    }
};

// 데이터 로딩 함수
const dataLoader = {
    async loadStats() {
        try {
            const stats = await api.getStats(7);
            
            elements.totalCount.textContent = stats.total_count.toLocaleString();
            elements.highRiskCount.textContent = stats.high_risk_count.toLocaleString();
            elements.spamCount.textContent = stats.spam_count.toLocaleString();
            elements.avgScore.textContent = stats.avg_score.toFixed(1);
            
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
                <td>${log.id}</td>
                <td>${utils.formatDate(log.created_at)}</td>
                <td class="text-preview" title="${log.text}">${utils.truncateText(log.text)}</td>
                <td class="${utils.getScoreClass(log.score)}">${utils.formatScore(log.score)} <br><small>(${utils.formatScore(log.confidence)})</small></td>
                <td class="${utils.getSpamClass(log.spam)}">${utils.formatScore(log.spam)} <br><small>(${utils.formatScore(log.confidence)})</small></td>
                <td>${utils.createTypeTags(log.types)}</td>
                <td>${log.ip_address || '-'}</td>
                <td>${log.response_time ? log.response_time.toFixed(3) + 's' : '-'}</td>
                <td>
                    <button class="btn-delete" onclick="event.stopPropagation(); deleteManager.showDeleteModal(${log.id}, '${log.text.replace(/'/g, "\\'")}', ${log.score})">
                        <i class="fas fa-trash-alt"></i>
                        <span>삭제</span>
                    </button>
                </td>
            `;
            
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
            <div class="detail-row">
                <div class="detail-label">비윤리점수 (신뢰도):</div>
                <div class="detail-value">
                    <span class="${utils.getScoreClass(log.score)}">${utils.formatScore(log.score)} <small>(${utils.formatScore(log.confidence)})</small></span>
                </div>
            </div>
            <div class="detail-row">
                <div class="detail-label">스팸지수 (신뢰도):</div>
                <div class="detail-value">${utils.formatScore(log.spam)} <small>(${utils.formatScore(log.confidence)})</small></div>
            </div>
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
        `;
        
        elements.logModal.classList.add('show');
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
        
        const scoreFilter = elements.scoreFilter.value;
        if (scoreFilter) {
            const [min, max] = scoreFilter.split('-').map(Number);
            if (min !== undefined) currentFilters.min_score = min;
            if (max !== undefined) currentFilters.max_score = max;
        }
        
        const days = parseInt(elements.dateFilter.value);
        if (days) {
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(endDate.getDate() - days);
            
            currentFilters.start_date = startDate.toISOString().split('T')[0];
            currentFilters.end_date = endDate.toISOString().split('T')[0];
        }
        
        await dataLoader.loadLogs();
        this.applyClientFilters();
    },
    
    applyClientFilters() {
        let tempFilteredLogs = [...originalLogs];
        
        const spamFilter = elements.spamFilter.value;
        if (spamFilter) {
            const [min, max] = spamFilter.split('-').map(Number);
            tempFilteredLogs = tempFilteredLogs.filter(log => {
                const spam = parseFloat(log.spam);
                return spam >= min && spam <= max;
            });
        }
        
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
        elements.dateFilter.value = '7';
        elements.searchInput.value = '';
        currentFilters = {};
        currentPage = 0;
        allLogs = [...originalLogs];
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
    },
    
    hideDeleteOldModal() {
        elements.deleteOldModal.classList.remove('show');
    },
    
    async previewDeleteCount() {
        const days = parseInt(elements.deleteDays.value);
        
        try {
            utils.showLoading();
            
            if (days === 0) {
                const response = await api.getStats(365);
                elements.previewCount.textContent = response.total_count || 0;
            } else {
                const response = await api.getStats(days);
                elements.previewCount.textContent = response.total_count || 0;
            }
            
        } catch (error) {
            console.error('Preview failed:', error);
            elements.previewCount.textContent = '-';
        } finally {
            utils.hideLoading();
        }
    },
    
    async confirmDeleteOld() {
        const days = parseInt(elements.deleteDays.value);
        
        try {
            utils.showLoading();
            const result = await api.deleteOldLogs(days);
            
            await dataLoader.loadLogs();
            await dataLoader.loadStats();
            
            this.hideDeleteOldModal();
            deleteManager.showSuccessMessage(`${result.deleted_count}개의 오래된 로그가 삭제되었습니다.`);
            
        } catch (error) {
            console.error('Old logs delete failed:', error);
            deleteManager.showErrorMessage('오래된 로그 삭제에 실패했습니다: ' + error.message);
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
        
        elements.spamFilter.addEventListener('change', () => {
            filterManager.applyClientFilters();
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
        
        elements.previewDelete.addEventListener('click', () => {
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
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (elements.logModal.classList.contains('show')) {
                    elements.logModal.classList.remove('show');
                } else if (elements.deleteModal.classList.contains('show')) {
                    deleteManager.hideDeleteModal();
                } else if (elements.deleteOldModal.classList.contains('show')) {
                    oldLogsManager.hideDeleteOldModal();
                }
            }
        });
    }
};

// 초기화
const app = {
    async init() {
        try {
            eventListeners.init();
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
})();

