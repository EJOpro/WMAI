// 신고내역 관리 시스템 JavaScript

// 전역 변수
let reportsData = [];
let filteredReports = [];
let currentPage = 1;
let itemsPerPage = 25;
let charts = {};

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// 앱 초기화
function initializeApp() {
    loadDataFromServer(); // 서버에서 먼저 로드 시도
    setupEventListeners();
    initializeCharts();
}

// 서버에서 데이터 로드
function loadDataFromServer() {
    fetch('/api/reports/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                reportsData = data.data;
                filteredReports = [...reportsData];
                renderDashboard();
                renderReportsList();
                updateFilterCounts();
            }
        })
        .catch(error => {
            console.error('데이터 로드 오류:', error);
            loadDummyData(); // 오류 시 더미 데이터 사용
        });
}

// 더미 데이터 로드 (백업용 - 일치/부분일치/불일치 포함)
function loadDummyData() {
    reportsData = [
        {
            id: 1,
            reportDate: '2025-10-16 18:30:45',
            reportType: '욕설 및 비방',
            reportedContent: '이런 바보 같은 정책은 누가 만든 거야? 정말 머리가 없는 것 같다.',
            reportReason: '욕설 및 비방',
            reporterId: 'user123',
            aiAnalysis: {
                result: '일치',
                confidence: 92,
                analysis: '게시글에 "바보", "머리가 없는" 등의 비방성 표현이 명확히 포함되어 있습니다.'
            },
            status: 'completed',
            priority: 'high',
            assignedTo: 'AI_System',
            processedDate: '2025-10-16 18:30:50',
            processingNote: 'AI 자동 처리: 신고 내용과 일치하여 게시글 삭제',
            postStatus: 'deleted',
            postAction: '게시글이 자동 삭제되었습니다.'
        },
        {
            id: 2,
            reportDate: '2025-10-16 17:22:33',
            reportType: '저작권 침해',
            reportedContent: '유명 작가의 소설 일부를 인용합니다. "삶이란 무엇인가..." (출처: XX작가, XX소설)',
            reportReason: '저작권 침해',
            reporterId: 'user101',
            aiAnalysis: {
                result: '부분일치',
                confidence: 65,
                analysis: '저작물 인용이 있으나 출처가 명시되어 있어 부분적으로만 문제가 될 수 있습니다.'
            },
            status: 'pending',
            priority: 'medium',
            assignedTo: null,
            processedDate: null,
            processingNote: null,
            postStatus: 'pending_review',
            postAction: null
        },
        {
            id: 3,
            reportDate: '2025-10-16 16:15:20',
            reportType: '욕설 및 비방',
            reportedContent: '오늘 날씨가 정말 좋네요. 공원에서 산책하면서 좋은 시간을 보냈습니다.',
            reportReason: '욕설 및 비방',
            reporterId: 'user789',
            aiAnalysis: {
                result: '불일치',
                confidence: 95,
                analysis: '게시글은 단순한 일상 공유 내용으로 욕설이나 비방 요소가 전혀 없습니다.'
            },
            status: 'rejected',
            priority: 'low',
            assignedTo: 'AI_System',
            processedDate: '2025-10-16 16:15:25',
            processingNote: 'AI 자동 처리: 신고 내용과 불일치하여 게시글 유지',
            postStatus: 'maintained',
            postAction: '게시글이 자동 유지되었습니다.'
        },
        {
            id: 4,
            reportDate: '2025-10-16 15:10:11',
            reportType: '도배 및 광고',
            reportedContent: '이 제품 정말 좋아요~ 친구들한테도 추천했는데 다들 만족해합니다. 혹시 관심있으시면 연락주세요.',
            reportReason: '도배 및 광고',
            reporterId: 'user202',
            aiAnalysis: {
                result: '부분일치',
                confidence: 72,
                analysis: '제품 추천 내용이 포함되어 있으나 명시적인 광고나 판매 의도는 불분명합니다.'
            },
            status: 'pending',
            priority: 'medium',
            assignedTo: null,
            processedDate: null,
            processingNote: null,
            postStatus: 'pending_review',
            postAction: null
        }
    ];
    
    filteredReports = [...reportsData];
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 필터 체크박스
    document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', applyFilters);
    });
    
    // 필터 적용 버튼
    document.getElementById('applyFilter').addEventListener('click', applyFilters);
    
    // 검색 입력
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    
    // 정렬 선택
    document.getElementById('sortBy').addEventListener('change', applySorting);
    
    // AI 분석 결과 필터
    document.getElementById('aiResultFilter').addEventListener('change', function() {
        const partialMatchSubFilter = document.getElementById('partialMatchSubFilter');
        if (this.value === '부분일치') {
            partialMatchSubFilter.style.display = 'block';
        } else {
            partialMatchSubFilter.style.display = 'none';
            partialMatchSubFilter.value = 'all';
        }
        applyFilters();
    });
    
    // 부분일치 서브필터
    document.getElementById('partialMatchSubFilter').addEventListener('change', applyFilters);
    
    // 페이지당 항목 수
    document.getElementById('itemsPerPage').addEventListener('change', function() {
        itemsPerPage = parseInt(this.value);
        currentPage = 1;
        renderReportsList();
    });
    
    // 빠른 액션 버튼들
    document.getElementById('refreshData').addEventListener('click', refreshData);
    document.getElementById('exportData').addEventListener('click', exportData);
    document.getElementById('bulkAction').addEventListener('click', showBulkActionModal);
    
    // 뷰 전환 버튼
    document.getElementById('listView').addEventListener('click', () => switchView('list'));
    document.getElementById('cardView').addEventListener('click', () => switchView('card'));
}

// 차트 초기화
function initializeCharts() {
    // 일별 신고 처리 현황 차트
    const dailyCtx = document.getElementById('dailyReportsChart').getContext('2d');
    charts.daily = new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: ['10/10', '10/11', '10/12', '10/13', '10/14', '10/15', '10/16'],
            datasets: [{
                label: '신규 신고',
                data: [12, 8, 15, 10, 18, 7, 5],
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                tension: 0.4
            }, {
                label: '처리 완료',
                data: [10, 12, 9, 14, 11, 16, 8],
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // 신고 유형별 분포 차트
    const typeCtx = document.getElementById('reportTypeChart').getContext('2d');
    charts.type = new Chart(typeCtx, {
        type: 'doughnut',
        data: {
            labels: ['욕설 및 비방', '도배 및 광고', '사생활 침해', '저작권 침해'],
            datasets: [{
                data: [35, 28, 22, 15],
                backgroundColor: [
                    '#dc3545',
                    '#ffc107',
                    '#17a2b8',
                    '#6f42c1'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                }
            }
        }
    });
    
    // 월별 트렌드 차트
    const monthlyCtx = document.getElementById('monthlyTrendChart').getContext('2d');
    charts.monthly = new Chart(monthlyCtx, {
        type: 'bar',
        data: {
            labels: ['8월', '9월', '10월'],
            datasets: [{
                label: '신고 접수',
                data: [245, 198, 176],
                backgroundColor: '#007bff'
            }, {
                label: '처리 완료',
                data: [231, 186, 165],
                backgroundColor: '#28a745'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
    
    // 처리 시간 분석 차트
    const timeCtx = document.getElementById('processingTimeChart').getContext('2d');
    charts.time = new Chart(timeCtx, {
        type: 'radar',
        data: {
            labels: ['1시간 이내', '1-4시간', '4-8시간', '8-24시간', '1일 이상'],
            datasets: [{
                label: '처리 시간 분포',
                data: [25, 45, 20, 8, 2],
                backgroundColor: 'rgba(0, 123, 255, 0.2)',
                borderColor: '#007bff',
                pointBackgroundColor: '#007bff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    max: 50
                }
            }
        }
    });
}

// 대시보드 렌더링
function renderDashboard() {
    const pending = reportsData.filter(r => r.status === 'pending').length;
    const completed = reportsData.filter(r => r.status === 'completed').length;
    const rejected = reportsData.filter(r => r.status === 'rejected').length;
    
    document.getElementById('pendingReports').textContent = pending;
    document.getElementById('completedReports').textContent = completed;
    document.getElementById('rejectedReports').textContent = rejected;
    
    // AI 정확도 계산 (더미 데이터)
    const accuracy = 87.3;
    document.getElementById('aiAccuracy').textContent = accuracy + '%';
    
    // 대시보드 카드 클릭 이벤트 추가
    setupDashboardClickEvents();
}

// 대시보드 카드 클릭 이벤트 설정
function setupDashboardClickEvents() {
    // 대기중 신고 카드 클릭 이벤트 (첫 번째 metric-card)
    const pendingCard = document.querySelector('.col-md-3:nth-child(1) .metric-card');
    if (pendingCard) {
        pendingCard.style.cursor = 'pointer';
        pendingCard.onclick = function() {
            showPendingReports();
        };
    }
    
    // 승인된 신고 카드 클릭 이벤트 (두 번째 metric-card)
    const completedCard = document.querySelector('.col-md-3:nth-child(2) .metric-card');
    if (completedCard) {
        completedCard.style.cursor = 'pointer';
        completedCard.onclick = function() {
            showCompletedReports();
        };
    }
}

// 대기중 신고 목록 표시
function showPendingReports() {
    // 신고 목록 탭으로 전환
    switchToReportsTab();
    
    // 모든 필터 초기화
    resetAllFilters();
    
    // 대기중 상태만 체크
    document.getElementById('statusPending').checked = true;
    document.getElementById('statusCompleted').checked = false;
    document.getElementById('statusRejected').checked = false;
    
    // 필터 적용
    applyFilters();
    
    // 알림 메시지
    showAlert('대기중인 신고 목록을 표시합니다.', 'info');
}

// 승인된 신고 목록 표시
function showCompletedReports() {
    // 신고 목록 탭으로 전환
    switchToReportsTab();
    
    // 모든 필터 초기화
    resetAllFilters();
    
    // 승인된 상태만 체크
    document.getElementById('statusPending').checked = false;
    document.getElementById('statusCompleted').checked = true;
    document.getElementById('statusRejected').checked = false;
    
    // 필터 적용
    applyFilters();
    
    // 알림 메시지
    showAlert('승인된 신고 목록을 표시합니다.', 'success');
}

// 반려된 신고 목록 표시
function showRejectedReports() {
    // 신고 목록 탭으로 전환
    switchToReportsTab();
    
    // 모든 필터 초기화
    resetAllFilters();
    
    // 반려된 상태만 체크
    document.getElementById('statusPending').checked = false;
    document.getElementById('statusCompleted').checked = false;
    document.getElementById('statusRejected').checked = true;
    
    // 필터 적용
    applyFilters();
    
    // 알림 메시지
    showAlert('반려된 신고 목록을 표시합니다.', 'danger');
}


// 신고 목록 탭으로 전환
function switchToReportsTab() {
    // 탭 시스템 사용하여 신고 목록 탭으로 전환
    const reportsTab = document.querySelector('a[href="#reports"]');
    if (reportsTab) {
        const tabInstance = new bootstrap.Tab(reportsTab);
        tabInstance.show();
    }
}

// 모든 필터 초기화
function resetAllFilters() {
    // 상태 필터 초기화
    document.getElementById('statusPending').checked = true;
    document.getElementById('statusCompleted').checked = true;
    document.getElementById('statusRejected').checked = true;
    
    // 유형 필터 초기화
    document.getElementById('typeAbuse').checked = true;
    document.getElementById('typeSpam').checked = true;
    document.getElementById('typePrivacy').checked = true;
    document.getElementById('typeCopyright').checked = true;
    
    // AI 결과 필터 초기화
    document.getElementById('aiResultFilter').value = 'all';
    document.getElementById('partialMatchSubFilter').style.display = 'none';
    document.getElementById('partialMatchSubFilter').value = 'all';
    
    // 검색어 초기화
    document.getElementById('searchInput').value = '';
    
    // 날짜 필터 초기화
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    
    // 정렬 초기화
    document.getElementById('sortBy').value = 'date';
}

// 필터 카운트 업데이트
function updateFilterCounts() {
    const pending = reportsData.filter(r => r.status === 'pending').length;
    const completed = reportsData.filter(r => r.status === 'completed').length;
    const rejected = reportsData.filter(r => r.status === 'rejected').length;
    
    document.getElementById('pendingCount').textContent = pending;
    document.getElementById('completedCount').textContent = completed;
    document.getElementById('rejectedCount').textContent = rejected;
}

// 필터 적용
function applyFilters() {
    filteredReports = reportsData.filter(report => {
        // 상태 필터
        const statusFilters = {
            pending: document.getElementById('statusPending').checked,
            completed: document.getElementById('statusCompleted').checked,
            rejected: document.getElementById('statusRejected').checked
        };
        
        if (!statusFilters[report.status]) return false;
        
        // 유형 필터
        const typeFilters = {
            '욕설 및 비방': document.getElementById('typeAbuse').checked,
            '도배 및 광고': document.getElementById('typeSpam').checked,
            '사생활 침해': document.getElementById('typePrivacy').checked,
            '저작권 침해': document.getElementById('typeCopyright').checked
        };
        
        if (!typeFilters[report.reportType]) return false;
        
        // AI 분석 결과 필터
        const aiResultFilter = document.getElementById('aiResultFilter').value;
        if (aiResultFilter !== 'all') {
            const aiResult = report.aiAnalysis ? report.aiAnalysis.result : '부분일치';
            if (aiResult !== aiResultFilter) return false;
            
            // 부분일치인 경우 서브필터 적용
            if (aiResultFilter === '부분일치') {
                const partialMatchSubFilter = document.getElementById('partialMatchSubFilter').value;
                if (partialMatchSubFilter !== 'all') {
                    const isReviewed = report.status === 'completed' || report.status === 'rejected';
                    if (partialMatchSubFilter === 'pending' && isReviewed) return false;
                    if (partialMatchSubFilter === 'reviewed' && !isReviewed) return false;
                }
            }
        }
        
        // 검색 필터
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        if (searchTerm && !report.reportedContent.toLowerCase().includes(searchTerm)) {
            return false;
        }
        
        // 날짜 필터
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        if (startDate || endDate) {
            const reportDate = new Date(report.reportDate).toISOString().split('T')[0];
            if (startDate && reportDate < startDate) return false;
            if (endDate && reportDate > endDate) return false;
        }
        
        return true;
    });
    
    currentPage = 1;
    applySorting();
}

// 정렬 적용
function applySorting() {
    const sortBy = document.getElementById('sortBy').value;
    const aiResultFilter = document.getElementById('aiResultFilter').value;
    
    filteredReports.sort((a, b) => {
        // 부분일치 필터가 선택된 경우, 관리자 검토가 필요한 글을 우선 정렬
        if (aiResultFilter === '부분일치') {
            const aIsReviewed = a.status === 'completed' || a.status === 'rejected';
            const bIsReviewed = b.status === 'completed' || b.status === 'rejected';
            
            // 검토가 필요한 글(pending)을 위로
            if (!aIsReviewed && bIsReviewed) return -1;
            if (aIsReviewed && !bIsReviewed) return 1;
        }
        
        // 기본 정렬 로직
        switch (sortBy) {
            case 'date':
                return new Date(b.reportDate) - new Date(a.reportDate);
            case 'status':
                const statusOrder = { pending: 0, completed: 1, rejected: 2 };
                return statusOrder[a.status] - statusOrder[b.status];
            case 'type':
                return a.reportType.localeCompare(b.reportType);
            case 'priority':
                const priorityOrder = { high: 0, medium: 1, low: 2 };
                return priorityOrder[a.priority] - priorityOrder[b.priority];
            default:
                return 0;
        }
    });
    
    renderReportsList();
}

// 신고 목록 렌더링
function renderReportsList() {
    const container = document.getElementById('reportsContainer');
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageReports = filteredReports.slice(startIndex, endIndex);
    
    if (pageReports.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <h5>신고가 없습니다</h5>
                <p class="text-muted">현재 필터 조건에 맞는 신고가 없습니다.</p>
            </div>
        `;
        renderPagination();
        return;
    }
    
    container.innerHTML = pageReports.map(report => `
        <div class="card report-card fade-in" data-report-id="${report.id}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge ${getStatusBadgeClass(report.status)} status-badge">
                        ${getStatusText(report.status)}
                    </span>
                    <span class="badge bg-secondary ms-2">${report.reportType}</span>
                    <span class="badge ${getPriorityBadgeClass(report.priority)} ms-2">
                        ${getPriorityText(report.priority)}
                    </span>
                </div>
                <small class="text-muted">${formatDate(report.reportDate)}</small>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-8">
                        <h6 class="card-title">신고된 내용</h6>
                        <p class="card-text">${truncateText(report.reportedContent, 150)}</p>
                        
                        <div class="ai-result ${getAiResultClass(report.aiAnalysis.result)}">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <strong>AI 분석 결과: ${report.aiAnalysis.result}</strong>
                                <span class="confidence-score ${getConfidenceClass(report.aiAnalysis.confidence)}">
                                    ${report.aiAnalysis.confidence}%
                                </span>
                            </div>
                            <small>${report.aiAnalysis.analysis}</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="mb-2">
                            <small class="text-muted">신고자:</small>
                            <div>${report.reporterId}</div>
                        </div>
                        ${report.assignedTo ? `
                            <div class="mb-2">
                                <small class="text-muted">담당자:</small>
                                <div>${report.assignedTo}</div>
                            </div>
                        ` : ''}
                        ${report.processingNote ? `
                            <div class="mb-2">
                                <small class="text-muted">처리 메모:</small>
                                <div><small>${report.processingNote}</small></div>
                            </div>
                        ` : ''}
                        ${report.postAction ? `
                            <div class="mb-2">
                                <small class="text-muted">게시글 처리:</small>
                                <div><small class="fw-bold ${report.postStatus === 'deleted' ? 'text-danger' : 'text-success'}">${report.postAction}</small></div>
                            </div>
                        ` : ''}
                        
                        <div class="action-buttons mt-3">
                            <button class="btn btn-sm btn-outline-primary" onclick="viewReportDetail(${report.id})">
                                <i class="fas fa-eye"></i> 상세보기
                            </button>
                            ${report.aiAnalysis.result === '부분일치' && report.status === 'pending' ? `
                                <button class="btn btn-sm btn-success" onclick="processReport(${report.id}, 'approve')">
                                    <i class="fas fa-check"></i> 승인
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="processReport(${report.id}, 'reject')">
                                    <i class="fas fa-times"></i> 반려
                                </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
    
    renderPagination();
}

// 페이지네이션 렌더링
function renderPagination() {
    const totalPages = Math.ceil(filteredReports.length / itemsPerPage);
    const pagination = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // 이전 페이지
    paginationHTML += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">이전</a>
        </li>
    `;
    
    // 페이지 번호들
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>
        `;
    }
    
    // 다음 페이지
    paginationHTML += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">다음</a>
        </li>
    `;
    
    pagination.innerHTML = paginationHTML;
}

// 페이지 변경
function changePage(page) {
    const totalPages = Math.ceil(filteredReports.length / itemsPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        renderReportsList();
    }
}

// 신고 상세보기
function viewReportDetail(reportId) {
    const report = reportsData.find(r => r.id === reportId);
    if (!report) return;
    
    const modalBody = document.querySelector('#reportDetailModal .modal-body');
    modalBody.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6>기본 정보</h6>
                <table class="table table-sm">
                    <tr><td><strong>신고 ID:</strong></td><td>${report.id}</td></tr>
                    <tr><td><strong>신고일시:</strong></td><td>${formatDate(report.reportDate)}</td></tr>
                    <tr><td><strong>신고 유형:</strong></td><td>${report.reportType}</td></tr>
                    <tr><td><strong>신고자:</strong></td><td>${report.reporterId}</td></tr>
                    <tr><td><strong>상태:</strong></td><td><span class="badge ${getStatusBadgeClass(report.status)}">${getStatusText(report.status)}</span></td></tr>
                    <tr><td><strong>우선순위:</strong></td><td><span class="badge ${getPriorityBadgeClass(report.priority)}">${getPriorityText(report.priority)}</span></td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>처리 정보</h6>
                <table class="table table-sm">
                    <tr><td><strong>담당자:</strong></td><td>${report.assignedTo || '미배정'}</td></tr>
                    <tr><td><strong>처리일시:</strong></td><td>${report.processedDate ? formatDate(report.processedDate) : '미처리'}</td></tr>
                    <tr><td><strong>처리 메모:</strong></td><td>${report.processingNote || '없음'}</td></tr>
                </table>
            </div>
        </div>
        
        <hr>
        
        <h6>신고된 내용</h6>
        <div class="bg-light p-3 rounded">
            ${report.reportedContent}
        </div>
        
        <hr>
        
        <h6>AI 분석 결과</h6>
        <div class="ai-result ${getAiResultClass(report.aiAnalysis.result)}">
            <div class="d-flex justify-content-between align-items-center mb-2">
                <strong>판단 결과: ${report.aiAnalysis.result}</strong>
                <span class="confidence-score ${getConfidenceClass(report.aiAnalysis.confidence)}">
                    신뢰도: ${report.aiAnalysis.confidence}%
                </span>
            </div>
            <p class="mb-0">${report.aiAnalysis.analysis}</p>
        </div>
    `;
    
    // 모달 버튼 설정 (부분일치만 승인/반려 가능)
    const approveBtn = document.getElementById('approveReport');
    const rejectBtn = document.getElementById('rejectReport');
    
    if (report.aiAnalysis.result === '부분일치' && report.status === 'pending') {
        approveBtn.style.display = 'inline-block';
        rejectBtn.style.display = 'inline-block';
        approveBtn.onclick = () => processReport(reportId, 'approve');
        rejectBtn.onclick = () => processReport(reportId, 'reject');
    } else {
        approveBtn.style.display = 'none';
        rejectBtn.style.display = 'none';
    }
    
    // 모달 표시
    const modal = document.getElementById('reportDetailModal')._modalInstance;
    modal.show();
}

// 신고 처리
function processReport(reportId, action) {
    const report = reportsData.find(r => r.id === reportId);
    if (!report) return;
    
    const actionText = action === 'approve' ? '승인' : '반려';
    const note = prompt(`${actionText} 처리 메모를 입력하세요:`);
    
    if (note !== null) {
        const newStatus = action === 'approve' ? 'completed' : 'rejected';
        
        // 서버에 업데이트 요청
        fetch(`/api/reports/update/${reportId}?status=${newStatus}&processing_note=${encodeURIComponent(note)}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // 로컬 데이터 업데이트
                const updatedReport = data.data;
                Object.assign(report, updatedReport);
                
                // UI 업데이트
                applyFilters();
                renderDashboard();
                updateFilterCounts();
                
                // 게시글 처리 결과 메시지
                let postMessage = '';
                if (updatedReport.postAction) {
                    postMessage = `<br><strong>📝 ${updatedReport.postAction}</strong>`;
                }
                
                showAlert(`신고가 ${actionText} 처리되었습니다.${postMessage}`, 'success');
                
                // 모달이 열려있다면 닫기
                const modal = document.getElementById('reportDetailModal')._modalInstance;
                if (modal) modal.hide();
            } else {
                showAlert('처리 중 오류가 발생했습니다.', 'danger');
            }
        })
        .catch(error => {
            console.error('처리 오류:', error);
            showAlert('서버 오류가 발생했습니다.', 'danger');
        });
    }
}

// 뷰 전환
function switchView(viewType) {
    const listBtn = document.getElementById('listView');
    const cardBtn = document.getElementById('cardView');
    
    if (viewType === 'list') {
        listBtn.classList.add('active');
        cardBtn.classList.remove('active');
        // 리스트 뷰 구현 (추후 확장)
    } else {
        cardBtn.classList.add('active');
        listBtn.classList.remove('active');
        // 카드 뷰는 현재 기본 뷰
    }
}

// 데이터 새로고침
function refreshData() {
    showAlert('데이터를 새로고침하고 있습니다...', 'info');
    
    fetch('/api/reports/list')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                reportsData = data.data;
                filteredReports = [...reportsData];
                applyFilters();
                renderDashboard();
                updateFilterCounts();
                showAlert('데이터가 새로고침되었습니다.', 'success');
            }
        })
        .catch(error => {
            console.error('새로고침 오류:', error);
            showAlert('데이터 새로고침 중 오류가 발생했습니다.', 'danger');
        });
}

// 데이터 내보내기
function exportData() {
    const csvContent = generateCSV(filteredReports);
    downloadCSV(csvContent, 'reports_export.csv');
    showAlert('데이터가 내보내기되었습니다.', 'success');
}

// CSV 생성
function generateCSV(data) {
    const headers = ['ID', '신고일시', '신고유형', '신고내용', '상태', 'AI결과', '신뢰도', '처리일시'];
    const rows = data.map(report => [
        report.id,
        report.reportDate,
        report.reportType,
        `"${report.reportedContent.replace(/"/g, '""')}"`,
        report.status,
        report.aiAnalysis.result,
        report.aiAnalysis.confidence,
        report.processedDate || ''
    ]);
    
    return [headers, ...rows].map(row => row.join(',')).join('\n');
}

// CSV 다운로드
function downloadCSV(content, filename) {
    const blob = new Blob(['\ufeff' + content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 일괄 처리 모달 표시
function showBulkActionModal() {
    // 일괄 처리 기능 구현 (추후 확장)
    showAlert('일괄 처리 기능은 준비 중입니다.', 'info');
}

// 알림 메시지 표시
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close"></button>
    `;
    
    // 닫기 버튼 이벤트
    const closeBtn = alertDiv.querySelector('.btn-close');
    closeBtn.addEventListener('click', () => {
        alertDiv.remove();
    });
    
    document.body.appendChild(alertDiv);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}

// 유틸리티 함수들
function getStatusBadgeClass(status) {
    const classes = {
        pending: 'bg-warning text-dark',
        completed: 'bg-success',
        rejected: 'bg-danger'
    };
    return classes[status] || 'bg-secondary';
}

function getStatusText(status) {
    const texts = {
        pending: '대기중',
        completed: '승인',
        rejected: '반려'
    };
    return texts[status] || status;
}

function getPriorityBadgeClass(priority) {
    const classes = {
        high: 'bg-danger',
        medium: 'bg-warning text-dark',
        low: 'bg-success'
    };
    return classes[priority] || 'bg-secondary';
}

function getPriorityText(priority) {
    const texts = {
        high: '높음',
        medium: '보통',
        low: '낮음'
    };
    return texts[priority] || priority;
}

function getAiResultClass(result) {
    const classes = {
        '일치': 'match',
        '불일치': 'mismatch',
        '부분일치': 'partial'
    };
    return classes[result] || 'partial';
}

function getConfidenceClass(confidence) {
    if (confidence >= 80) return 'confidence-high';
    if (confidence >= 60) return 'confidence-medium';
    return 'confidence-low';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}
