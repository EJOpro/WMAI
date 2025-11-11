// 전역 변수
// 차트 변수 제거됨
let isAnalysisRunning = false;

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM 로드 완료, 초기화 시작...');
    
    // 약간의 지연을 두고 초기화 (DOM 완전 로드 보장)
    setTimeout(async () => {
        try {
            // 차트 초기화는 분석 후에만 수행
            setupEventListeners();
            
            // MySQL 데이터 상태 확인
            await checkAndDisplayMySQLDataStatus();
            
            await updateStatusCards(); // 초기 상태 카드 설정
            
            // 요약 카드 타이틀 초기 업데이트
            updateChurnCardTitle();
            
            // 초기 로그 추가
            addLog('시스템 초기화 완료', 'success');
            
            console.log('초기화 완료 (차트는 분석 후 표시)!');
        } catch (error) {
            console.error('초기화 중 오류 발생:', error);
            addLog('초기화 중 오류 발생: ' + error.message, 'danger');
        }
    }, 100);
});

// 이벤트 리스너 설정
function setupEventListeners() {
    console.log('setupEventListeners 함수 시작...');
    
    // 안전한 이벤트 리스너 추가 함수
    function safeAddEventListener(elementId, event, handler) {
        console.log(`요소 찾는 중: ${elementId}`);
        
        // 핸들러 함수 존재 확인
        if (typeof handler !== 'function') {
            console.error(`❌ 핸들러가 함수가 아닙니다: ${elementId} -> ${typeof handler}`);
            return;
        }
        
        const element = document.getElementById(elementId);
        if (element) {
            element.addEventListener(event, handler);
            console.log(`✅ 이벤트 리스너 추가됨: ${elementId}`);
        } else {
            console.warn(`❌ 요소를 찾을 수 없습니다: ${elementId}`);
        }
    }
    
    // 파일 업로드
    safeAddEventListener('csvFile', 'change', handleFileUpload);
    safeAddEventListener('uploadBtn', 'click', uploadFile);
    
    // 분석 실행
    safeAddEventListener('runAnalysisBtn', 'click', runAnalysis);
    
    // 설정 변경 감지
    safeAddEventListener('analysisMonth', 'change', updateAnalysisMonth);
    
    // 세그먼트 체크박스
    safeAddEventListener('channelSegment', 'change', updateSegmentOptions);
    safeAddEventListener('actionType', 'change', updateSegmentOptions);

}

// 차트 관련 기능 제거됨

// 파일 업로드 처리
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
            showAlert('CSV 파일만 업로드 가능합니다.', 'danger');
            event.target.value = '';
            return;
        }
        
        if (file.size > 50 * 1024 * 1024) { // 50MB 제한
            showAlert('파일 크기는 50MB를 초과할 수 없습니다.', 'danger');
            event.target.value = '';
            return;
        }
        
        addLog(`파일 선택됨: ${file.name} (${formatFileSize(file.size)})`, 'info');
        document.getElementById('uploadBtn').disabled = false;
        
        // 파일 선택 시에는 데이터 상태만 부분 업데이트
        updateDataStatusForSelectedFile(file);
    }
}

// 파일 업로드 실행
function uploadFile() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showAlert('업로드할 파일을 선택해주세요.', 'warning');
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>업로드 중...';
    
    // 업로드 진행 상태 표시
    updateDataStatusForUploading(file);
    
    // 파일 읽기 시뮬레이션
    setTimeout(() => {
        // CSV 파일 검증 시뮬레이션
        validateCSVFile(file).then(result => {
            if (result.success) {
                addLog(`파일 업로드 완료: ${result.rows}행 검증됨 (${result.dropped}행 제외)`, 'success');
                showAlert('파일이 성공적으로 업로드되었습니다.', 'success');
                updateProgressBar(25, '데이터 업로드 완료');
                
                // 상태 카드 즉시 업데이트
                updateStatusCards().then(() => {
                    addLog('대시보드 상태 업데이트 완료', 'info');
                });
            } else {
                addLog(`파일 업로드 실패: ${result.error}`, 'danger');
                showAlert(`업로드 실패: ${result.error}`, 'danger');
                
                // 실패 시 상태 원복
                updateDataStatusForSelectedFile(file);
            }
            
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-1"></i>업로드 실행';
        });
    }, 2000);
}

// CSV 파일 검증 및 파싱
function validateCSVFile(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const csv = e.target.result;
            const lines = csv.split('\n').filter(line => line.trim());
            
            if (lines.length < 2) {
                resolve({ success: false, error: '데이터가 없습니다.' });
                return;
            }
            
            const headers = lines[0].split(',').map(h => h.trim());
            const requiredColumns = ['user_hash', 'created_at', 'action', 'channel'];
            const missingColumns = requiredColumns.filter(col => !headers.includes(col));
            
            if (missingColumns.length > 0) {
                resolve({ 
                    success: false, 
                    error: `필수 컬럼 누락: ${missingColumns.join(', ')}` 
                });
                return;
            }
            
            // 실제 데이터 파싱
            const data = [];
            let droppedRows = 0;
            
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',').map(v => v.trim());
                if (values.length !== headers.length) {
                    droppedRows++;
                    continue;
                }
                
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index];
                });
                
                // 데이터 검증
                if (!row.user_hash || !row.created_at || !row.action) {
                    droppedRows++;
                    continue;
                }
                
                // action 검증
                if (!['post', 'comment'].includes(row.action)) {
                    droppedRows++;
                    continue;
                }
                
                // 날짜 파싱
                try {
                    row.date = new Date(row.created_at);
                    row.year_month = row.date.toISOString().substring(0, 7); // YYYY-MM
                } catch (e) {
                    droppedRows++;
                    continue;
                }
                
                // Unknown 값 보정
                row.channel = row.channel || 'Unknown';
                
                data.push(row);
            }
            
            // 전역 변수에 저장
            window.csvData = data;
            
            // 백엔드에 데이터 업로드
            uploadToBackend(data).then(async (backendResult) => {
                if (backendResult.success) {
                    console.log('[DEBUG] 백엔드 업로드 성공:', backendResult.message);
                    // 업로드 후 캐시 클리어하여 새로운 데이터 기반 분석이 되도록 함
                    const cacheResult = await clearBackendCache();
                    if (cacheResult.success) {
                        console.log('[DEBUG] 백엔드 캐시 클리어 완료');
                        addLog('백엔드 데이터 업로드 및 캐시 클리어 완료', 'success');
                    } else {
                        console.warn('[WARNING] 캐시 클리어 실패:', cacheResult.message);
                    }
                } else {
                    console.warn('[WARNING] 백엔드 업로드 실패:', backendResult.error);
                    addLog(`백엔드 업로드 실패: ${backendResult.error}`, 'warning');
                }
            });
            
            resolve({
                success: true,
                rows: data.length,
                dropped: droppedRows,
                data: data
            });
        };
        reader.readAsText(file);
    });
}

// 백엔드에 데이터 업로드
async function uploadToBackend(data) {
    try {
        // 먼저 기존 데이터 삭제 (새로운 데이터로 교체하기 위해)
        try {
            const clearResponse = await fetch('/api/churn/events/clear', {
                method: 'DELETE'
            });
            if (clearResponse.ok) {
                const clearResult = await clearResponse.json();
                console.log('[DEBUG] 기존 데이터 삭제 완료:', clearResult.message);
            } else {
                console.warn('[WARNING] 기존 데이터 삭제 실패:', clearResponse.status);
            }
        } catch (clearError) {
            console.warn('[WARNING] 기존 데이터 삭제 중 오류:', clearError);
            // 삭제 실패해도 업로드는 계속 진행
        }
        
        // 백엔드 형식에 맞게 변환
        const events = data.map(row => ({
            user_hash: row.user_hash,
            created_at: row.created_at,
            action: row.action,
            channel: row.channel === 'Unknown' ? null : row.channel
        }));
        
        // 데이터가 너무 많으면 청크로 나누어 전송
        const chunkSize = 1000;
        for (let i = 0; i < events.length; i += chunkSize) {
            const chunk = events.slice(i, i + chunkSize);
            const response = await fetch('/api/churn/events/bulk', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(chunk)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.warn(`[WARNING] 백엔드 업로드 청크 ${Math.floor(i / chunkSize) + 1} 실패:`, errorText);
                throw new Error(`청크 ${Math.floor(i / chunkSize) + 1} 업로드 실패: ${response.status}`);
            }
        }
        
        return { success: true, message: `${events.length}개 이벤트 업로드 완료` };
    } catch (error) {
        console.error('[ERROR] 백엔드 업로드 오류:', error);
        return { success: false, error: error.message };
    }
}

// 분석 실행
async function runAnalysis() {
    if (isAnalysisRunning) return;
    
    // MySQL 데이터 상태 확인
    const dataStatus = await checkBackendDataStatus();
    const hasCSVData = window.csvData && window.csvData.length > 0;
    
    if (!dataStatus.has_data && !hasCSVData) {
        showAlert('분석할 데이터가 없습니다. CSV 파일을 업로드하거나 MySQL 데이터베이스에 데이터가 있는지 확인해주세요.', 'warning');
        return;
    }
    
    isAnalysisRunning = true;
    const runBtn = document.getElementById('runAnalysisBtn');
    runBtn.disabled = true;
    runBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>분석 실행 중...';
    
    // 분석 상태 업데이트
    updateAnalysisStatus('running');
    
    addLog('분석 시작...', 'info');
    updateProgressBar(0, '분석 초기화 중...');
    
    // 분석 단계별 실행 시뮬레이션
    const analysisSteps = [
        { progress: 10, message: '데이터 전처리 중...', delay: 1000 },
        { progress: 25, message: '월별 활성 사용자 집계 중...', delay: 1500 },
        { progress: 40, message: '이탈률 계산 중...', delay: 1200 },
        { progress: 55, message: '세그먼트 분석 중...', delay: 1800 },
        { progress: 70, message: '장기 미접속 사용자 분석 중...', delay: 1000 },
        
        { progress: 95, message: '리포트 생성 중...', delay: 1000 },
        { progress: 100, message: '분석 완료!', delay: 500 }
    ];
    
    executeAnalysisSteps(analysisSteps, 0);
}

// 분석 단계별 실행
async function executeAnalysisSteps(steps, currentStep) {
    if (currentStep >= steps.length) {
        completeAnalysis();
        return;
    }
    
    const step = steps[currentStep];
    
    setTimeout(async () => {
        updateProgressBar(step.progress, step.message);
        addLog(`[${getCurrentTime()}] ${step.message}`, 'info');
        
        // 특정 단계에서 데이터 업데이트
        if (step.progress === 40) {
            await updateMetricCards();
        } else if (step.progress === 95) {
            await updateReportWithDynamicData();
        }
        
        executeAnalysisSteps(steps, currentStep + 1);
    }, step.delay);
}

// 분석 완료
function completeAnalysis() {
    isAnalysisRunning = false;
    const runBtn = document.getElementById('runAnalysisBtn');
    runBtn.disabled = false;
    runBtn.innerHTML = '<i class="fas fa-play me-2"></i>분석 실행';
    
    // 분석 상태 업데이트
    updateAnalysisStatus('completed');
    
    addLog('분석이 성공적으로 완료되었습니다!', 'success');
    
    showAlert('분석이 완료되었습니다! 리포트 탭에서 결과를 확인하세요.', 'success');
    
    // 리포트 탭으로 자동 전환 (Bootstrap 없이 동작)
    setTimeout(() => {
        const reportTabLink = document.querySelector('.tab-link[data-tab="#report"]') || document.querySelector('a[href="#report"]');
        if (reportTabLink) {
            // 모든 탭/패널 비활성화
            document.querySelectorAll('.tab-link').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
            // 대상 활성화
            reportTabLink.classList.add('active');
            const pane = document.querySelector('#report');
            if (pane) pane.classList.add('active');
        }
    }, 2000);
}

// 지표 카드 업데이트 (백엔드 API 사용)
async function updateMetricCards() {
    // MySQL 데이터 상태 확인
    const dataStatus = await checkBackendDataStatus();
    const hasCSVData = window.csvData && window.csvData.length > 0;
    
    if (!dataStatus.has_data && !hasCSVData) {
        // 메트릭 카드 숨기기
        document.getElementById('metricsRow').style.display = 'none';
        addLog('데이터가 없어서 지표를 표시하지 않습니다.', 'warning');
        return;
    }
    
    try {
        // 백엔드 API 호출로 통일된 계산 결과 사용
        const config = getCurrentConfig();
        console.log('[DEBUG] updateMetricCards - 현재 설정:', config);
        
        const backendResponse = await callBackendAPI(config);
        console.log('[DEBUG] updateMetricCards - 백엔드 응답:', backendResponse);
        
        // 백엔드 응답 저장 (토글 전환 시 사용)
        currentBackendResponse = backendResponse;
        
        // 백엔드 응답에서 메트릭과 세그먼트 데이터 분리
        const metrics = {
            churn_rate: backendResponse.churn_rate,
            active_users: backendResponse.active_users,
            previous_active_users: backendResponse.previous_active_users,
            churned_users: backendResponse.churned_users,
            reactivated_users: backendResponse.reactivated_users,
            long_term_inactive: backendResponse.long_term_inactive,
            // 범위 지표 추가
        };
        
        // 백엔드 응답 스냅샷 출력 (화면 숫자와 일치 확인용)
        console.log('[BE 응답 스냅샷]', JSON.stringify(backendResponse, null, 2));
        
        // 세그먼트 분석 결과를 별도 API로 가져오기
        const month = config.month || '2025-10';
        
        // 선택된 세그먼트 확인
        const channelSelected = config.segments?.channel || false;
        const actionTypeSelected = config.segments?.action_type || false;
        
        // 선택된 세그먼트가 있으면 API 호출
        if (channelSelected || actionTypeSelected) {
            try {
                const params = new URLSearchParams({
                    start_month: month,
                    end_month: month,
                    channel: channelSelected ? 'true' : 'false',
                    action_type: actionTypeSelected ? 'true' : 'false'
                });
                
                const segmentResponse = await fetch(`/api/churn/analysis/segments?${params}`);
                if (segmentResponse.ok) {
                    const segmentData = await segmentResponse.json();
                    window.currentSegmentAnalysis = segmentData;
                    console.log('[DEBUG] 세그먼트 분석 결과 저장 (별도 API):', window.currentSegmentAnalysis);
                    console.log('[DEBUG] - channel:', segmentData.channel);
                    console.log('[DEBUG] - action_type:', segmentData.action_type);
                    console.log('[DEBUG] - weekday_pattern:', segmentData.weekday_pattern);
                    console.log('[DEBUG] - time_pattern:', segmentData.time_pattern);
                    
                    // 세그먼트 분석 결과를 화면에 표시
                    displaySegmentAnalysisResults(segmentData);
                } else {
                    console.warn('[WARNING] 세그먼트 분석 API 호출 실패:', segmentResponse.status);
                    // 백엔드 응답의 segments 객체 사용 (fallback)
                    if (backendResponse.segments) {
                        window.currentSegmentAnalysis = backendResponse.segments;
                        console.log('[DEBUG] 세그먼트 분석 결과 저장 (fallback):', window.currentSegmentAnalysis);
                        displaySegmentAnalysisResults(backendResponse.segments);
                    }
                }
            } catch (error) {
                console.error('[ERROR] 세그먼트 분석 API 호출 중 오류:', error);
                // 백엔드 응답의 segments 객체 사용 (fallback)
                if (backendResponse.segments) {
                    window.currentSegmentAnalysis = backendResponse.segments;
                    console.log('[DEBUG] 세그먼트 분석 결과 저장 (fallback):', window.currentSegmentAnalysis);
                    displaySegmentAnalysisResults(backendResponse.segments);
                }
            }
        } else {
            console.log('[INFO] 세그먼트 분석이 선택되지 않았습니다.');
        }
        
        // 백엔드 오류 또는 빈 데이터인 경우 프론트엔드 계산 사용
        const hasError = metrics.error !== undefined;
        const hasNoData = !metrics.churn_rate && !metrics.active_users && !metrics.reactivated_users;
        const isBackendDataEmpty = hasError || hasNoData;
        
        if (isBackendDataEmpty) {
            if (metrics.error) {
                console.warn('[WARNING] 백엔드 계산 실패');
            }
            // CSV 데이터가 있으면 프론트엔드 계산 사용, 없으면 에러 메시지
            if (hasCSVData) {
                const fallbackMetrics = calculateMetrics(window.csvData, config);
                console.log('[DEBUG] 프론트엔드 계산 결과:', fallbackMetrics);
                updateMetricCardsWithData(fallbackMetrics, config);
                addLog('프론트엔드 로컬 계산 완료', 'success');
            } else {
                addLog('MySQL 데이터가 있지만 분석 결과를 가져올 수 없습니다. 데이터 범위를 확인해주세요.', 'warning');
                document.getElementById('metricsRow').style.display = 'none';
            }
            return;
        }
        
        // 메트릭 카드 표시
        document.getElementById('metricsRow').style.display = 'flex';
        
        // 백엔드에서 받은 데이터로 업데이트
        updateMetricCardsWithBackendResponse(backendResponse, config);
        
        addLog('백엔드 API를 통한 정확한 계산 완료', 'success');
        
    } catch (error) {
        addLog(`API 호출 실패: ${error.message}`, 'warning');
        
        // CSV 데이터가 있으면 프론트엔드 계산 사용, 없으면 에러 메시지
        if (hasCSVData) {
            const fallbackConfig = getCurrentConfig();
            console.log('[DEBUG] 폴백 계산 - 설정:', fallbackConfig);
            const fallbackMetrics = calculateMetrics(window.csvData, fallbackConfig);
            console.log('[DEBUG] 폴백 계산 - 결과:', fallbackMetrics);
            updateMetricCardsWithData(fallbackMetrics, fallbackConfig);
            addLog('로컬 계산으로 폴백 실행', 'info');
        } else {
            addLog('MySQL 데이터 분석 중 오류가 발생했습니다. 데이터 범위를 확인해주세요.', 'error');
            document.getElementById('metricsRow').style.display = 'none';
        }
    }
}

// 백엔드 응답으로 메트릭 카드 업데이트 (월별/범위 지표 지원)
function updateMetricCardsWithBackendResponse(backendResponse, config) {
    if (!backendResponse) return;
    
    // 월별 지표 사용
    const metrics = {
        churn_rate: backendResponse.churn_rate || 0,
        active_users: backendResponse.active_users || 0,
        previous_active_users: backendResponse.previous_active_users || 0,
        churned_users: backendResponse.churned_users || 0,
        retained_users: backendResponse.retained_users || 0,
        reactivated_users: backendResponse.reactivated_users || 0,
        long_term_inactive: backendResponse.long_term_inactive || 0
    };
    
    // 카드 제목 업데이트
    updateCardTitles();
    
    // 메트릭 카드 업데이트
    updateMetricCardsWithData(metrics, config);
}

// 카드 제목 업데이트
function updateCardTitles() {
    const churnCardTitle = document.getElementById('churnCardTitle');
    const activeUsersCardTitle = document.getElementById('activeUsersCardTitle');
    const activeUsersSubtext = document.getElementById('activeUsersSubtext');
    
    if (churnCardTitle) churnCardTitle.textContent = '이탈률';
    if (activeUsersCardTitle) activeUsersCardTitle.textContent = '활성 사용자';
    if (activeUsersSubtext) {
        activeUsersSubtext.innerHTML = '증감률 <strong id="userGrowthRate">-</strong>';
    }
}

// 메트릭 카드 데이터 업데이트 (공통 함수)
function updateMetricCardsWithData(metrics, config) {
    // 메트릭 카드 표시
    document.getElementById('metricsRow').style.display = 'flex';
    
    // 실제 계산된 값으로 업데이트
    animateValue('churnRate', metrics.churn_rate || metrics.churnRate || 0, '%');
    animateValue('activeUsers', metrics.active_users || metrics.activeUsers || 0, '');
    animateValue('reactivatedUsers', metrics.reactivated_users || metrics.reactivatedUsers || 0, '');
    animateValue('longTermInactive', metrics.long_term_inactive || metrics.longTermInactive || 0, '');
    
    // 새로운 동적 지표들 업데이트 (백엔드 형식에 맞춰 조정)
    const normalizedMetrics = {
        churnRate: metrics.churn_rate || metrics.churnRate || 0,
        activeUsers: metrics.active_users || metrics.activeUsers || 0,
        previousActiveUsers: metrics.previous_active_users || metrics.previousActiveUsers || 0,
        reactivatedUsers: metrics.reactivated_users || metrics.reactivatedUsers || 0,
        longTermInactive: metrics.long_term_inactive || metrics.longTermInactive || 0
    };
    
    updateAdvancedMetrics(normalizedMetrics, config);
    
    // 요약 카드 타이틀 업데이트
    updateChurnCardTitle();
    
    // 헤더 정보 업데이트 (절대기간, 임계값, 선택 세그먼트)
    updateAnalysisHeaderInfo();
    
    // 툴팁 초기화 (공식 표시)
    initializeTooltips();
}

// 요약 카드 타이틀 업데이트 (범위 모드에서는 "이전월/현재월" 라벨 숨김)
function updateChurnCardTitle() {
    const titleElement = document.getElementById('churnCardTitle');
    
    if (!titleElement) return;
    
    titleElement.textContent = '이탈률';
}

// 헤더 정보 업데이트 (절대기간, 임계값, 선택 세그먼트)
function updateAnalysisHeaderInfo() {
    const config = getCurrentConfig();
    const headerInfo = document.getElementById('analysisHeaderInfo');
    
    if (!headerInfo) return;
    
    const month = config.month || '';
    // threshold는 기본값 1 (이벤트 1회 이상)
    const threshold = 1;
    
    // 절대기간 계산 (YYYY-MM-DD 형식)
    let periodText = '-';
    if (month) {
        const startDate = new Date(month + '-01');
        const endDate = new Date(month + '-01');
        // 마지막 날짜 계산
        endDate.setMonth(endDate.getMonth() + 1);
        endDate.setDate(0); // 해당 월의 마지막 날
        
        const startDateStr = startDate.toISOString().substring(0, 10);
        const endDateStr = endDate.toISOString().substring(0, 10);
        periodText = `${startDateStr} ~ ${endDateStr}`;
    }
    
    // 선택된 세그먼트 확인
    const segments = [];
    if (config.segments?.channel) segments.push('채널');
    if (config.segments?.action_type) segments.push('이벤트 타입');
    const segmentsText = segments.length > 0 ? segments.join(', ') : '없음';
    
    // 헤더 정보 업데이트
    document.getElementById('headerPeriod').textContent = periodText;
    document.getElementById('headerThreshold').textContent = `이벤트 ${threshold}회 이상`;
    document.getElementById('headerSegments').textContent = segmentsText;
    
    // 헤더 표시
    headerInfo.style.display = 'block';
}

// 툴팁 초기화 및 공식 표시
function initializeTooltips() {
    const config = getCurrentConfig();
    const month = config.month || '';
    // threshold는 기본값 1 (이벤트 1회 이상)
    const threshold = 1;
    const inactivityDays = 90; // 장기 미접속 임계값
    
    // 이탈률 공식 툴팁
    const churnTooltip = document.getElementById('churnFormulaTooltip');
    if (churnTooltip) {
        let formulaText = '';
        formulaText = `월별 이탈률 공식:\nchurn_m = churned_m / active_{m-1}\n\n`;
        formulaText += `월: ${month}\n`;
        formulaText += `이전 월 대비 현재 월 이탈률`;
        
        formulaText += `\n임계값: 이벤트 ${threshold}회 이상`;
        
        // 세그먼트 필터 정보 추가
        const segments = [];
        if (config.segments?.channel) segments.push('채널');
        if (config.segments?.action_type) segments.push('이벤트 타입');
        if (segments.length > 0) {
            formulaText += `\n세그먼트 필터: ${segments.join(', ')}`;
        }
        
        churnTooltip.setAttribute('title', formulaText);
        churnTooltip.setAttribute('data-original-title', formulaText);
        
        // 마우스 호버 시 툴팁 표시
        churnTooltip.addEventListener('mouseenter', function() {
            showTooltip(this, formulaText);
        });
        
        // 키보드 접근성: Enter/Space 키로 툴팁 표시
        churnTooltip.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                showTooltip(this, formulaText);
            }
        });
    }
    
    // 장기 미접속 임계값 툴팁
    const inactiveTooltip = document.getElementById('inactiveThresholdTooltip');
    if (inactiveTooltip) {
        let inactiveText = `장기 미접속 임계값: ${inactivityDays}일\n\n`;
        inactiveText += `${inactivityDays}일 이상 활동이 없는 사용자를 장기 미접속으로 분류`;
        
        const segments = [];
        if (config.segments?.channel) segments.push('채널');
        if (config.segments?.action_type) segments.push('이벤트 타입');
        if (segments.length > 0) {
            inactiveText += `\n\n세그먼트 필터: ${segments.join(', ')} 반영`;
        }
        
        inactiveTooltip.setAttribute('title', inactiveText);
        inactiveTooltip.setAttribute('data-original-title', inactiveText);
        
        // 마우스 호버 시 툴팁 표시
        inactiveTooltip.addEventListener('mouseenter', function() {
            showTooltip(this, inactiveText);
        });
        
        // 키보드 접근성: Enter/Space 키로 툴팁 표시
        inactiveTooltip.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                showTooltip(this, inactiveText);
            }
        });
    }
}

// 툴팁 표시 함수 (접근성 고려)
function showTooltip(element, text) {
    // 간단한 툴팁 구현 (Bootstrap 없이)
    const existingTooltip = document.getElementById('customTooltip');
    if (existingTooltip) {
        existingTooltip.remove();
    }
    
    const tooltip = document.createElement('div');
    tooltip.id = 'customTooltip';
    tooltip.className = 'custom-tooltip';
    tooltip.textContent = text;
    tooltip.style.cssText = `
        position: absolute;
        background: #333;
        color: #fff;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 0.875rem;
        white-space: pre-line;
        z-index: 1000;
        max-width: 300px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = element.getBoundingClientRect();
    tooltip.style.top = (rect.top - tooltip.offsetHeight - 8) + 'px';
    tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
    
    // 마우스/포커스 벗어나면 제거
    const removeTooltip = () => {
        if (tooltip.parentNode) {
            tooltip.remove();
        }
    };
    
    element.addEventListener('mouseleave', removeTooltip, { once: true });
    element.addEventListener('blur', removeTooltip, { once: true });
    
    // ESC 키로 닫기
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            removeTooltip();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// 백엔드 데이터 상태 확인
async function checkBackendDataStatus() {
    try {
        const response = await fetch('/api/churn/data/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error('[ERROR] 데이터 상태 확인 실패:', error);
        return { has_data: false, total_events: 0, unique_users: 0 };
    }
}



// 백엔드 API 호출
async function callBackendAPI(config) {
    // 먼저 데이터 상태 확인
    const dataStatus = await checkBackendDataStatus();
    
    if (!dataStatus.has_data) {
        // CSV 데이터가 있으면 계속 진행
        if (!window.csvData || window.csvData.length === 0) {
            throw new Error('데이터베이스에 데이터가 없습니다. CSV 파일을 업로드하거나 MySQL 데이터를 생성해주세요.');
        }
    }
    
    const month = config.month || '2025-10';
    const inactivityThresholds = [30, 60, 90];
    
    // 월별 분석이므로 start_month와 end_month를 동일하게 설정
    const requestData = {
        start_month: month,
        end_month: month,
        segments: {
            channel: config.segments?.channel ?? false,
            action_type: config.segments?.action_type ?? false
        },
        inactivity_days: inactivityThresholds,
        threshold: 1  // 최소 이벤트 수
    };
    
    console.log('[DEBUG] callBackendAPI - 요청 데이터:', requestData);
    
    const response = await fetch('/api/churn/analysis/run', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    return result.metrics || result;
}

// 백엔드 캐시 무효화
async function clearBackendCache() {
    try {
        const response = await fetch('/api/churn/cache/clear', {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            console.warn('캐시 삭제 API 호출 실패:', response.status);
            return { success: false, message: '캐시 삭제 실패' };
        }
        
        const result = await response.json();
        console.log('[DEBUG] 캐시 삭제 결과:', result);
        return { success: true, message: result.message };
    } catch (error) {
        console.error('캐시 삭제 중 오류:', error);
        return { success: false, message: error.message };
    }
}

// 상태 카드 업데이트
async function updateStatusCards() {
    // 데이터 상태 업데이트 (async)
    await updateDataStatus();
    
    // 기간 상태 업데이트
    updatePeriodStatus();

    
    // 분석 상태 업데이트
    updateAnalysisStatus();
}

// MySQL 데이터 상태 확인 및 표시
async function checkAndDisplayMySQLDataStatus() {
    try {
        const dataStatus = await checkBackendDataStatus();
        
        if (dataStatus.has_data) {
            // MySQL 데이터가 있으면 CSV 업로드 섹션 숨기기
            const uploadCard = document.querySelector('.card:has(#csvFile)');
            if (uploadCard) {
                uploadCard.style.display = 'none';
            }
            
            addLog(`MySQL 데이터베이스에 ${dataStatus.total_events.toLocaleString()}개의 이벤트가 있습니다 (사용자: ${dataStatus.unique_users}명)`, 'success');
            
            // 데이터 범위 표시
            if (dataStatus.oldest_date && dataStatus.latest_date) {
                addLog(`데이터 기간: ${new Date(dataStatus.oldest_date).toLocaleDateString()} ~ ${new Date(dataStatus.latest_date).toLocaleDateString()}`, 'info');
            }
        } else {
            addLog('MySQL 데이터베이스에 데이터가 없습니다. CSV 파일을 업로드하거나 데이터를 생성해주세요.', 'info');
        }
    } catch (error) {
        console.error('MySQL 데이터 상태 확인 실패:', error);
        addLog('MySQL 데이터 상태 확인 실패', 'warning');
    }
}

// 데이터 상태 업데이트
async function updateDataStatus() {
    const dataStatus = document.getElementById('dataStatus');
    const dataInfo = document.getElementById('dataInfo');
    
    // MySQL 데이터 상태 확인
    const mysqlStatus = await checkBackendDataStatus();
    
    if (window.csvData && window.csvData.length > 0) {
        dataStatus.textContent = '로드됨 (CSV)';
        dataStatus.className = 'card-title text-success';
        dataInfo.textContent = `${window.csvData.length.toLocaleString()}행 데이터`;
        
        // 아이콘 색상 변경 (스피너에서 파일 아이콘으로 복원)
        const icon = dataStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-file-csv fa-2x text-success mb-2';
    } else if (mysqlStatus.has_data) {
        dataStatus.textContent = '로드됨 (MySQL)';
        dataStatus.className = 'card-title text-success';
        dataInfo.textContent = `${mysqlStatus.total_events.toLocaleString()}개 이벤트 (${mysqlStatus.unique_users}명 사용자)`;
        
        // 아이콘을 데이터베이스 아이콘으로 변경
        const icon = dataStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-database fa-2x text-success mb-2';
    } else {
        dataStatus.textContent = '데이터 없음';
        dataStatus.className = 'card-title text-secondary';
        dataInfo.textContent = 'CSV 파일을 업로드하거나 MySQL 데이터를 확인하세요';
        
        // 아이콘 색상 원복
        const icon = dataStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-file-csv fa-2x text-secondary mb-2';
    }
}

// 파일 선택 시 데이터 상태 부분 업데이트
function updateDataStatusForSelectedFile(file) {
    const dataStatus = document.getElementById('dataStatus');
    const dataInfo = document.getElementById('dataInfo');
    
    if (file) {
        dataStatus.textContent = '선택됨';
        dataStatus.className = 'card-title text-warning';
        dataInfo.textContent = `${file.name} (${formatFileSize(file.size)})`;
        
        // 아이콘 색상 변경
        const icon = dataStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-file-csv fa-2x text-warning mb-2';
    }
}

// 업로드 진행 중 상태 표시
function updateDataStatusForUploading(file) {
    const dataStatus = document.getElementById('dataStatus');
    const dataInfo = document.getElementById('dataInfo');
    
    if (file) {
        dataStatus.textContent = '처리중';
        dataStatus.className = 'card-title text-info';
        dataInfo.textContent = `${file.name} 파싱 중...`;
        
        // 아이콘 색상 변경 (스피너 효과)
        const icon = dataStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-spinner fa-spin fa-2x text-info mb-2';
    }
}





// 기간 상태 업데이트
function updatePeriodStatus() {
    const periodStatus = document.getElementById('periodStatus');
    const periodInfo = document.getElementById('periodInfo');
    const analysisMonth = document.getElementById('analysisMonth')?.value;
    
    if (analysisMonth) {
        periodStatus.textContent = '설정됨';
        periodStatus.className = 'card-title text-success';
        periodInfo.textContent = analysisMonth;
        
        // 아이콘 색상 변경
        const icon = periodStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-calendar-alt fa-2x text-success mb-2';
    } else {
        periodStatus.textContent = '미설정';
        periodStatus.className = 'card-title text-secondary';
        periodInfo.textContent = '월을 선택하세요';
        
        // 아이콘 색상 원복
        const icon = periodStatus.parentElement.querySelector('i[class*="fa-"]');
        if (icon) icon.className = 'fas fa-calendar-alt fa-2x text-info mb-2';
    }
}

// 분석 상태 업데이트
function updateAnalysisStatus(status = 'waiting') {
    const analysisStatus = document.getElementById('analysisStatus');
    const analysisInfo = document.getElementById('analysisInfo');
    const icon = analysisStatus.parentElement.querySelector('i[class*="fa-"]');
    
    switch (status) {
        case 'running':
            analysisStatus.textContent = '실행중';
            analysisStatus.className = 'card-title text-warning';
            analysisInfo.textContent = '분석 진행중...';
            if (icon) icon.className = 'fas fa-chart-line fa-2x text-warning mb-2';
            break;
        case 'completed':
            analysisStatus.textContent = '완료';
            analysisStatus.className = 'card-title text-success';
            analysisInfo.textContent = '분석이 완료되었습니다';
            if (icon) icon.className = 'fas fa-chart-line fa-2x text-success mb-2';
            break;
        case 'error':
            analysisStatus.textContent = '오류';
            analysisStatus.className = 'card-title text-danger';
            analysisInfo.textContent = '분석 중 오류 발생';
            if (icon) icon.className = 'fas fa-chart-line fa-2x text-danger mb-2';
            break;
        default: // waiting
            analysisStatus.textContent = '대기중';
            analysisStatus.className = 'card-title text-secondary';
            analysisInfo.textContent = '분석 실행을 클릭하세요';
            if (icon) icon.className = 'fas fa-chart-line fa-2x text-secondary mb-2';
    }
}

// 고급 지표 업데이트
function updateAdvancedMetrics(metrics, config) {
    // 1. 이탈률 심각도 및 이탈자 수
    // 백엔드가 제공하는 churned_users를 직접 사용 (재계산 금지)
    const churnRate = metrics.churn_rate || metrics.churnRate || 0;
    const churnedCount = metrics.churned_users || metrics.churnedCount || 
        (metrics.previous_active_users || metrics.previousActiveUsers ? 
            Math.round((metrics.previous_active_users || metrics.previousActiveUsers || 0) * churnRate / 100) : 0);
    
    updateElement('churnedCount', churnedCount);
    updateChurnSeverity(churnRate);
    
    // 2. 활성 사용자 트렌드 및 증감률
    const activeUsers = metrics.active_users || metrics.activeUsers || 0;
    const previousActiveUsers = metrics.previous_active_users || metrics.previousActiveUsers || 0;
    
    // 월별 모드일 때만 증감률 표시
    const growthRate = calculateGrowthRate(activeUsers, previousActiveUsers);
    const userGrowthRateEl = document.getElementById('userGrowthRate');
    if (userGrowthRateEl) {
        userGrowthRateEl.textContent = `${growthRate > 0 ? '+' : ''}${growthRate}%`;
    }
    updateUserTrend(growthRate);
    
    // 3. 재활성률 및 복귀 패턴
    const reactivatedUsers = metrics.reactivated_users || metrics.reactivatedUsers || 0;
    const longTermInactive = metrics.long_term_inactive || metrics.longTermInactive || 0;
    const reactivationRate = calculateReactivationRate(reactivatedUsers, longTermInactive);
    updateElement('reactivationRate', `${reactivationRate}%`);
    updateReturnPattern(reactivationRate);
    
    // 4. 위험도 레벨 및 손실 위험
    const riskPercentage = calculateRiskPercentage(longTermInactive, activeUsers);
    updateElement('lossRisk', `${riskPercentage}%`);
    updateRiskLevel(riskPercentage);
}

// 요소 업데이트 헬퍼 함수
function updateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

// 이탈률 심각도 업데이트
function updateChurnSeverity(churnRate) {
    const element = document.getElementById('churnSeverity');
    if (!element) return;
    
    if (churnRate >= 20) {
        element.textContent = '매우높음';
        element.className = 'badge bg-danger';
    } else if (churnRate >= 15) {
        element.textContent = '높음';
        element.className = 'badge bg-warning text-dark';
    } else if (churnRate >= 10) {
        element.textContent = '보통';
        element.className = 'badge bg-primary';
    } else {
        element.textContent = '낮음';
        element.className = 'badge bg-success';
    }
}

// 사용자 트렌드 업데이트
function updateUserTrend(growthRate) {
    const element = document.getElementById('userTrend');
    if (!element) return;
    
    // 범위 모드일 때는 null이 전달될 수 있음
    if (growthRate === null || growthRate === undefined) {
        element.textContent = '-';
        element.className = 'badge bg-secondary';
        return;
    }
    
    if (growthRate > 10) {
        element.textContent = '급성장';
        element.className = 'badge bg-success';
    } else if (growthRate > 5) {
        element.textContent = '성장';
        element.className = 'badge bg-info';
    } else if (growthRate > 0) {
        element.textContent = '소폭증가';
        element.className = 'badge bg-primary';
    } else if (growthRate > -5) {
        element.textContent = '안정';
        element.className = 'badge bg-secondary';
    } else if (growthRate > -10) {
        element.textContent = '감소';
        element.className = 'badge bg-warning text-dark';
    } else {
        element.textContent = '급감소';
        element.className = 'badge bg-danger';
    }
}

// 복귀 패턴 업데이트
function updateReturnPattern(reactivationRate) {
    const element = document.getElementById('returnPattern');
    if (!element) return;
    
    if (reactivationRate > 5) {
        element.textContent = '매우좋음';
    } else if (reactivationRate > 3) {
        element.textContent = '좋음';
    } else if (reactivationRate > 1) {
        element.textContent = '보통';
    } else {
        element.textContent = '나쁨';
    }
}

// 위험도 레벨 업데이트
function updateRiskLevel(riskPercentage) {
    const element = document.getElementById('riskLevel');
    if (!element) return;
    
    if (riskPercentage > 15) {
        element.textContent = '고위험';
        element.className = 'badge bg-danger';
    } else if (riskPercentage > 10) {
        element.textContent = '중위험';
        element.className = 'badge bg-warning text-dark';
    } else {
        element.textContent = '저위험';
        element.className = 'badge bg-success';
    }
}

// 계산 헬퍼 함수들
function calculateGrowthRate(current, previous) {
    if (!previous || previous === 0) return 0;
    return Math.round(((current - previous) / previous) * 100 * 10) / 10;
}

function calculateReactivationRate(reactivated, longTermInactive) {
    const total = reactivated + longTermInactive;
    if (total === 0) return 0;
    return Math.round((reactivated / total) * 100 * 10) / 10;
}

function calculateRiskPercentage(longTermInactive, activeUsers) {
    const total = longTermInactive + activeUsers;
    if (total === 0) return 0;
    return Math.round((longTermInactive / total) * 100 * 10) / 10;
}

// 차트 기능 제거됨

// 값 애니메이션
function animateValue(elementId, targetValue, suffix = '') {
    const element = document.getElementById(elementId);
    const startValue = 0;
    const duration = 1000;
    const startTime = performance.now();
    
    function updateValue(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const currentValue = startValue + (targetValue - startValue) * easeOutQuart(progress);
        
        if (suffix === '%') {
            element.textContent = currentValue.toFixed(1) + suffix;
        } else {
            element.textContent = Math.floor(currentValue).toLocaleString() + suffix;
        }
        
        if (progress < 1) {
            requestAnimationFrame(updateValue);
        }
    }
    
    requestAnimationFrame(updateValue);
}

// 이징 함수
function easeOutQuart(t) {
    return 1 - Math.pow(1 - t, 4);
}

// 진행률 바 업데이트
function updateProgressBar(progress, message) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressBar.style.width = progress + '%';
    progressBar.setAttribute('aria-valuenow', progress);
    progressText.textContent = message;
    
    // 진행률에 따른 색상 변경
    progressBar.className = 'progress-bar';
    if (progress < 30) {
        progressBar.classList.add('bg-info');
    } else if (progress < 70) {
        progressBar.classList.add('bg-warning');
    } else {
        progressBar.classList.add('bg-success');
    }
}

// 로그 추가 (개발자도구 콘솔로 출력)
function addLog(message, type = 'info') {
    const timestamp = getCurrentTime();
    const logMessage = `[${timestamp}] ${message}`;
    
    // 개발자도구 콘솔에 출력
    switch(type) {
        case 'error':
        case 'danger':
            console.error(logMessage);
            break;
        case 'warning':
            console.warn(logMessage);
            break;
        case 'success':
            console.log(`✅ ${logMessage}`);
            break;
        case 'info':
        default:
            console.log(`ℹ️ ${logMessage}`);
            break;
    }
}

// 지표 타입 전역 변수 (월별/범위)
let currentBackendResponse = null; // 백엔드 응답 저장

// 현재 시간 가져오기
function getCurrentTime() {
    return new Date().toLocaleTimeString('ko-KR', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 알림 표시
function showAlert(message, type) {
    // 기존 알림 제거
    const existingAlert = document.querySelector('.alert');
    if (existingAlert) {
        existingAlert.remove();
    }

    const alert = document.createElement('div');
    // Bootstrap 없이도 보이도록 기본 클래스만 사용
    alert.className = `alert alert-${type}`;
    alert.textContent = message;

    const main = document.querySelector('main');
    main.insertBefore(alert, main.firstChild);

    // 자동 제거
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// 파일 크기 포맷팅
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}


// 분석 월 변경 핸들러
async function updateAnalysisMonth() {
    const analysisMonth = document.getElementById('analysisMonth')?.value;
    
    console.log('[UI] analysisMonth=' + analysisMonth);
    
    if (analysisMonth) {
        // 캐시 무효화
        try {
            await clearBackendCache();
            addLog('이전 분석 결과 캐시가 삭제되었습니다', 'success');
        } catch (error) {
            console.warn('캐시 삭제 실패:', error);
        }
        
        // 전역 세그먼트 분석 결과 초기화
        window.currentSegmentAnalysis = null;
        
        // 상태 카드 업데이트
        await updateStatusCards();
        
        // 요약 카드 타이틀 업데이트
        updateChurnCardTitle();
        
        // 기간 상태 업데이트
        updatePeriodStatus();
        
        addLog(`분석 월 변경: ${analysisMonth}`, 'info');
    }
}


async function updateSegmentOptions() {
    const channelElement = document.getElementById('channelSegment');
    const actionTypeElement = document.getElementById('actionType');
    
    const channel = channelElement ? channelElement.checked : false;
    const actionType = actionTypeElement ? actionTypeElement.checked : false;
    
    const segments = [];
    if (channel) segments.push('채널');
    if (actionType) segments.push('이벤트타입');
    
    if (segments.length === 0) {
        addLog('세그먼트 옵션 변경: 모든 세그먼트 해제됨', 'info');
    } else {
        addLog(`세그먼트 옵션 변경: ${segments.join(', ')}`, 'info');
    }
    
    // 캐시 무효화 (세그먼트 변경 시)
    try {
        await clearBackendCache();
    } catch (error) {
        console.warn('세그먼트 변경 시 캐시 삭제 실패:', error);
    }
    
    // 전역 세그먼트 분석 결과 초기화
    window.currentSegmentAnalysis = null;
    
    // 데이터가 있고 분석이 완료된 상태라면 메트릭을 즉시 업데이트
    if (window.csvData && window.csvData.length > 0) {
        // 메트릭도 다시 계산 (세그먼트 변경이 일부 계산에 영향을 줄 수 있음)
        await updateMetricCards();
    }
}


// 키보드 단축키
document.addEventListener('keydown', function(e) {
    // Ctrl + Enter: 분석 실행
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        if (!isAnalysisRunning) {
            runAnalysis();
        }
    }
    
    // Esc: 진행 중인 작업 취소 (향후 구현)
    if (e.key === 'Escape' && isAnalysisRunning) {
        // 취소 로직 구현 가능
    }
});

// 차트 리사이즈 기능 제거됨

// 실제 지표 계산 함수 (날짜 기반)
function calculateMetrics(data, config = {}) {
    const startDate = config.startDate || '2025-08-01';
    const endDate = config.endDate || '2025-10-31';

    const inactivityThreshold = 90;
    const endMonth = endDate.substring(0, 7);
    
    console.log(`[DEBUG] calculateMetrics 호출됨 - 기간: ${startDate} ~ ${endDate}`);
    console.log(`[DEBUG] 설정:`, config);
    console.log(`[DEBUG] 세그먼트 설정:`, config.segments);
    
    // 데이터 유효성 검사
    if (!data || !Array.isArray(data) || data.length === 0) {
        console.warn('[WARNING] calculateMetrics: 데이터가 없습니다');
        return {
            churnRate: 0,
            activeUsers: 0,
            reactivatedUsers: 0,
            longTermInactive: 0,
            previousActiveUsers: 0
        };
    }
    
    console.log(`[DEBUG] 데이터 행 수: ${data.length}`);
    console.log(`[DEBUG] 비활성 임계값: ${inactivityThreshold}일`);
    
    // 날짜 범위 내 데이터 필터링
    const filteredData = data.filter(row => {
        if (!row.created_at) return false;
        const rowDate = new Date(row.created_at).toISOString().split('T')[0];
        return rowDate >= startDate && rowDate <= endDate;
    });
    
    console.log(`[DEBUG] 필터링된 데이터: ${filteredData.length}행`);
    
    // 기간을 반으로 나누어 전반기/후반기 비교
    const start = new Date(startDate);
    const end = new Date(endDate);
    const midPoint = new Date(start.getTime() + (end.getTime() - start.getTime()) / 2);
    const midDateStr = midPoint.toISOString().split('T')[0];
    
    // 전반기와 후반기 사용자 분리
    const firstHalfUsers = new Set();
    const secondHalfUsers = new Set();
    
    filteredData.forEach(row => {
        const rowDate = new Date(row.created_at).toISOString().split('T')[0];
        if (rowDate <= midDateStr) {
            firstHalfUsers.add(row.user_hash);
        } else {
            secondHalfUsers.add(row.user_hash);
        }
    });
    
    const firstHalfCount = firstHalfUsers.size;
    const secondHalfCount = secondHalfUsers.size;
    
    console.log(`[DEBUG] 전반기 사용자: ${firstHalfCount}, 후반기 사용자: ${secondHalfCount}`);
    
    // 이탈률 계산 (전반기에는 있었지만 후반기에는 없는 사용자)
    let churnRate = 0;
    let churnedCount = 0;
    if (firstHalfCount > 0) {
        const churnedUsers = [...firstHalfUsers].filter(user => !secondHalfUsers.has(user));
        churnedCount = churnedUsers.length;
        churnRate = (churnedCount / firstHalfCount) * 100;
        console.log(`[DEBUG] 이탈자 수: ${churnedCount}, 이탈률: ${churnRate}%`);
    }
    
    // 재활성 사용자 계산 (후반기에만 있는 사용자)
    const reactivatedUsers = [...secondHalfUsers].filter(user => !firstHalfUsers.has(user)).length;
    
    // 장기 미접속 사용자 (설정된 임계값 기준)
    const longTermInactive = calculateLongTermInactive(data, endMonth, inactivityThreshold);
    
    const result = {
        churnRate: Math.round(churnRate * 10) / 10,
        activeUsers: secondHalfCount,
        previousActiveUsers: firstHalfCount,
        reactivatedUsers: reactivatedUsers,
        longTermInactive: longTermInactive,
        totalUsers: new Set(filteredData.map(row => row.user_hash)).size,
        totalEvents: filteredData.length
    };
    
    console.log(`[DEBUG] 최종 계산 결과:`, result);
    return result;
}

// 차트 데이터 계산 기능 제거됨

// 세그먼트별 차트 계산 기능 제거됨

// 특정 세그먼트의 이탈률 계산 (전체 기간 집계)
function calculateSegmentChurnRateFullRange(data, segmentType, segmentValue, months) {
    const segmentData = data.filter(row => row[segmentType] === segmentValue);
    console.log(`[DEBUG] ${segmentType}=${segmentValue}: 필터된 데이터 ${segmentData.length}건`);
    
    const activeUsersByMonth = {};
    segmentData.forEach(row => {
        if (!activeUsersByMonth[row.year_month]) {
            activeUsersByMonth[row.year_month] = new Set();
        }
        activeUsersByMonth[row.year_month].add(row.user_hash);
    });
    
    let totalPreviousActive = 0;
    let totalChurned = 0;
    
    // 모든 월 전환에 대해 집계
    for (let i = 1; i < months.length; i++) {
        const previousMonth = months[i - 1];
        const currentMonth = months[i];
        
        const currentSet = activeUsersByMonth[currentMonth] || new Set();
        const previousSet = activeUsersByMonth[previousMonth] || new Set();
        
        if (previousSet.size > 0) {
            totalPreviousActive += previousSet.size;
            const churnedUsers = [...previousSet].filter(user => !currentSet.has(user));
            totalChurned += churnedUsers.length;
            
            console.log(`[DEBUG] ${segmentType}=${segmentValue}: ${previousMonth}->${currentMonth} 이전:${previousSet.size}명, 이탈:${churnedUsers.length}명`);
        }
    }
    
    if (totalPreviousActive === 0) {
        console.log(`[DEBUG] ${segmentType}=${segmentValue}: 전체 기간 이전 월 데이터 없음`);
        return null;
    }
    
    const churnRate = (totalChurned / totalPreviousActive) * 100;
    console.log(`[DEBUG] ${segmentType}=${segmentValue}: 전체 기간 이전활성:${totalPreviousActive}명, 총이탈:${totalChurned}명, 이탈률:${churnRate}%`);
    
    return Math.round(churnRate * 10) / 10;
}

// 특정 세그먼트의 이탈률 계산 (단일 월 전환)
function calculateSegmentChurnRate(data, segmentType, segmentValue, previousMonth, currentMonth) {
    const segmentData = data.filter(row => row[segmentType] === segmentValue);
    console.log(`[DEBUG] ${segmentType}=${segmentValue}: 필터된 데이터 ${segmentData.length}건`);
    
    const activeUsersByMonth = {};
    segmentData.forEach(row => {
        if (!activeUsersByMonth[row.year_month]) {
            activeUsersByMonth[row.year_month] = new Set();
        }
        activeUsersByMonth[row.year_month].add(row.user_hash);
    });
    
    const currentSet = activeUsersByMonth[currentMonth] || new Set();
    const previousSet = activeUsersByMonth[previousMonth] || new Set();
    
    console.log(`[DEBUG] ${segmentType}=${segmentValue}: ${previousMonth}월 ${previousSet.size}명, ${currentMonth}월 ${currentSet.size}명`);
    
    if (previousSet.size === 0) {
        console.log(`[DEBUG] ${segmentType}=${segmentValue}: 이전 월 데이터 없음`);
        return null; // 이전 월 데이터 없음
    }
    
    const churnedUsers = [...previousSet].filter(user => !currentSet.has(user));
    const churnRate = (churnedUsers.length / previousSet.size) * 100;
    
    console.log(`[DEBUG] ${segmentType}=${segmentValue}: 이탈자 ${churnedUsers.length}명, 이탈률 ${churnRate}%`);
    
    return Math.round(churnRate * 10) / 10;
}

// 재활성 사용자 계산 (30일 이상 쉬었다가 복귀)
function calculateReactivatedUsers(data, currentMonth) {
    const currentDate = new Date(currentMonth + '-01');
    const thirtyDaysAgo = new Date(currentDate.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    // 현재 월 활성 사용자
    const currentActiveUsers = new Set();
    data.forEach(row => {
        if (row.year_month === currentMonth) {
            currentActiveUsers.add(row.user_hash);
        }
    });
    
    // 재활성 사용자 카운트
    let reactivatedCount = 0;
    currentActiveUsers.forEach(userId => {
        const userActivities = data.filter(row => row.user_hash === userId);
        userActivities.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        
        // 현재 월 이전 마지막 활동 찾기
        let lastActivityBeforeCurrent = null;
        for (let activity of userActivities) {
            if (activity.year_month < currentMonth) {
                lastActivityBeforeCurrent = new Date(activity.created_at);
            }
        }
        
        if (lastActivityBeforeCurrent && (currentDate - lastActivityBeforeCurrent) >= 30 * 24 * 60 * 60 * 1000) {
            reactivatedCount++;
        }
    });
    
    return reactivatedCount;
}

// 장기 미접속 사용자 계산 (90일 이상)
function calculateLongTermInactive(data, currentMonth, inactivityDays = 90) {
    const thresholdDays = 90;

    const currentDate = new Date(currentMonth + '-01');

    if (Number.isNaN(currentDate.getTime())) {
        return 0;
    }

    const cutoffDate = new Date(currentDate.getTime() - thresholdDays * 24 * 60 * 60 * 1000);    

    // 모든 사용자의 마지막 활동일 계산
    const userLastActivity = {};
    data.forEach(row => {
        if (!row || !row.user_hash || !row.created_at) return;

        const activityDate = new Date(row.created_at);

        if (Number.isNaN(activityDate.getTime()) || activityDate > currentDate) return;

        const userId = row.user_hash;
        if (!userLastActivity[userId] || activityDate > userLastActivity[userId]) {
            userLastActivity[userId] = activityDate;
        }
    });
    
    // 임계값 이상 미접속 사용자 카운트
    let longTermInactiveCount = 0;
    Object.values(userLastActivity).forEach(lastActivity => {
        if (lastActivity < cutoffDate) {
            longTermInactiveCount++;
        }
    });
    
    return longTermInactiveCount;
}

// 현재 UI 설정 가져오기
function getCurrentConfig() {
    const analysisMonth = document.getElementById('analysisMonth').value;
    
    return {
        month: analysisMonth,
        segments: {
            channel: document.getElementById('channelSegment') ? document.getElementById('channelSegment').checked : false,
            action_type: document.getElementById('actionType') ? document.getElementById('actionType').checked : false
        }
    };
}

// 월 범위 생성
function generateMonthRange(startMonth, endMonth) {
    const start = new Date(startMonth + '-01');
    const end = new Date(endMonth + '-01');
    const months = [];
    
    let current = new Date(start);
    while (current <= end) {
        const yearMonth = current.toISOString().substring(0, 7);
        months.push(yearMonth);
        current.setMonth(current.getMonth() + 1);
    }
    
    return months;
}

// 연령대 정렬 함수
function sortAgeBands(ageBands) {
    const ageOrder = ['10s', '20s', '30s', '40s', '50s', '60s'];
    return ageBands.sort((a, b) => {
        const aIndex = ageOrder.indexOf(a);
        const bIndex = ageOrder.indexOf(b);
        if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
        if (aIndex === -1) return 1;
        if (bIndex === -1) return -1;
        return aIndex - bIndex;
    });
}

// 연령대 표시 형식 변환 (10s → 10대)
function formatAgeBand(ageBand) {
    if (ageBand && ageBand.endsWith('s')) {
        return ageBand.replace('s', '대');
    }
    return ageBand;
}

// 이전 월 계산
function getPreviousMonth(month) {
    const date = new Date(month + '-01');
    date.setMonth(date.getMonth() - 1);
    return date.toISOString().substring(0, 7);
}

// 세그먼트 분석 결과를 화면에 표시
function displaySegmentAnalysisResults(segmentData) {
    const resultsContainer = document.getElementById('segmentAnalysisResults');
    if (!resultsContainer) {
        console.warn('[WARNING] segmentAnalysisResults 요소를 찾을 수 없습니다');
        return;
    }
    
    let html = '<ul class="plain-list">';
    
    // 각 세그먼트별 결과 표시
    Object.keys(segmentData).forEach(segmentType => {
        const segment = segmentData[segmentType];
        if (!segment || !Array.isArray(segment) || segment.length === 0) return;
        
        const segmentName = getSegmentDisplayName(segmentType);
        html += `<li class="mb-3"><strong style="color: var(--primary-color);">${segmentName}</strong></li>`;
        
        segment.forEach(item => {
            const churnRate = item.churn_rate ? item.churn_rate.toFixed(2) : '0.00';
            // 백엔드에서 current_active를 반환하므로 두 필드 모두 확인
            const activeUsers = item.current_active || item.active_users || 0;
            const churnedUsers = item.churned_users || item.churned || 0;
            
            // segment_value 한국어 변환
            let displayValue = item.segment_value;
            if (segmentType === 'action_type' || segmentType === 'action') {
                const actionNames = {
                    'view': '조회', 'login': '로그인', 'comment': '댓글',
                    'like': '좋아요', 'post': '게시글', 'mixed': '기타'
                };
                displayValue = actionNames[item.segment_value] || item.segment_value;
            } else if (segmentType === 'channel') {
                const channelNames = {
                    'web': '웹', 'app': '모바일 앱', 'Unknown': '알 수 없음'
                };
                displayValue = channelNames[item.segment_value] || item.segment_value;
            } else if (item.segment_value === '혼합') {
                displayValue = '기타';
            }
            
            const uncertainNote = item.is_uncertain ? ' <span style="color: #ff9800; font-size: 0.85em;">(표본 적음)</span>' : '';
            
            html += `
                <li class="mb-2" style="margin-left: 1rem;">
                    <i class="fas fa-circle" style="font-size: 0.5rem; color: var(--info-color); margin-right: .5rem;"></i>
                    <span style="font-weight: 600;">${displayValue}</span>: 
                    이탈률 <span style="color: var(--danger-color);">${churnRate}%</span> 
                    (활성: ${activeUsers.toLocaleString()}명, 이탈: ${churnedUsers.toLocaleString()}명)${uncertainNote}
                </li>
            `;
        });
    });
    
    html += '</ul>';
    resultsContainer.innerHTML = html;
    
    console.log('[DEBUG] 세그먼트 분석 결과 화면 표시 완료');
}

// 세그먼트 타입의 표시 이름 반환
function getSegmentDisplayName(segmentType) {
    const names = {
        'channel': '채널별',
        'action': '이벤트 타입별',
        'action_type': '이벤트 타입별',
        'weekday_pattern': '활동 요일 패턴별',
        'time_pattern': '활동 시간대별',
        'combined': '복합 세그먼트'
    };
    return names[segmentType] || segmentType;
}

// 세그먼트 데이터 필터링
function filterSegmentsByConfig(chartData, segmentConfig) {
    const labels = [];
    const data = [];
    const colors = [];
    
    if (!chartData.segmentLabels) return { labels, data, colors };
    
    chartData.segmentLabels.forEach((label, index) => {
        let shouldInclude = false;
        
        
        
        // 채널 세그먼트
        if (segmentConfig.channel && (label === '웹' || label === '앱')) {
            shouldInclude = true;
        }
        
        // 액션 타입 세그먼트
        if (segmentConfig.actionType && (label === '게시글' || label === '댓글' || label === '조회' || label === '좋아요' || label === '로그인')) {
            shouldInclude = true;
        }
        
        if (shouldInclude) {
            labels.push(label);
            data.push(chartData.segmentData[index]);
            if (chartData.segmentColors) {
                colors.push(chartData.segmentColors[index]);
            }
        }
    });
    
    return { labels, data, colors };
}

// 세그먼트 분석 (완전 동적)
function calculateSegmentAnalysis(data, config) {
    const segments = {};
    
    // 날짜 범위에서 월 추출
    const startDate = config.startDate || '2025-08-01';
    const endDate = config.endDate || '2025-10-31';
    const startMonth = startDate.substring(0, 7);
    const endMonth = endDate.substring(0, 7);
    
    console.log(`[DEBUG] calculateSegmentAnalysis - 기간: ${startMonth} ~ ${endMonth}`);
    
    // 날짜 범위 내 데이터 필터링
    const filteredData = data.filter(row => {
        if (!row.created_at) return false;
        const rowDate = new Date(row.created_at).toISOString().split('T')[0];
        return rowDate >= startDate && rowDate <= endDate;
    });
    
    console.log(`[DEBUG] 세그먼트 분석용 필터링된 데이터: ${filteredData.length}행`);
    
    
    // 채널 분석
    if (config.segments.channel) {
        segments.channel = analyzeSegmentByTypeFullRange(filteredData, 'channel', ['web', 'app'], startMonth, endMonth);
    }
    
    // 액션 타입 분석
    if (config.segments.action_type) {
        segments.action = analyzeSegmentByTypeFullRange(filteredData, 'action', ['post', 'comment', 'view', 'like', 'login'], startMonth, endMonth);
    }
    
    
    console.log(`[DEBUG] 세그먼트 분석 결과:`, segments);
    return segments;
}

// 특정 타입의 세그먼트 분석 (전체 기간 집계)
function analyzeSegmentByTypeFullRange(data, segmentType, segmentValues, startMonth, endMonth) {
    const results = [];
    
    // 분석할 월 범위 생성
    const months = generateMonthRange(startMonth, endMonth);
    if (months.length < 2) {
        console.log(`[DEBUG] ${segmentType} 분석: 충분한 월 데이터가 없음`);
        return [];
    }
    
    console.log(`[DEBUG] ${segmentType} 분석 기간:`, months);
    
    segmentValues.forEach(segmentValue => {
        // 해당 세그먼트의 데이터만 필터링
        const segmentData = data.filter(row => row[segmentType] === segmentValue);
        
        if (segmentData.length === 0) return;
        
        // 월별 활성 사용자 계산
        const activeUsersByMonth = {};
        segmentData.forEach(row => {
            if (!activeUsersByMonth[row.year_month]) {
                activeUsersByMonth[row.year_month] = new Set();
            }
            activeUsersByMonth[row.year_month].add(row.user_hash);
        });
        
        let totalPreviousActive = 0;
        let totalChurned = 0;
        let totalCurrentActive = 0;
        
        // 모든 월 전환에 대해 집계
        for (let i = 1; i < months.length; i++) {
            const previousMonth = months[i - 1];
            const currentMonth = months[i];
            
            const currentSet = activeUsersByMonth[currentMonth] || new Set();
            const previousSet = activeUsersByMonth[previousMonth] || new Set();
            
            if (previousSet.size > 0) {
                totalPreviousActive += previousSet.size;
                const churnedUsers = [...previousSet].filter(user => !currentSet.has(user));
                totalChurned += churnedUsers.length;
                
                console.log(`[DEBUG] ${segmentType}=${segmentValue}: ${previousMonth}->${currentMonth} 이전:${previousSet.size}명, 이탈:${churnedUsers.length}명`);
            }
            
            // 마지막 월의 현재 활성 사용자 수
            if (i === months.length - 1) {
                totalCurrentActive = currentSet.size;
            }
        }
        
        if (totalPreviousActive === 0) {
            console.log(`[DEBUG] ${segmentType}=${segmentValue}: 전체 기간 이전 월 데이터 없음`);
            return;
        }
        
        const churnRate = (totalChurned / totalPreviousActive) * 100;
        const isUncertain = totalPreviousActive < 30;
        
        console.log(`[DEBUG] ${segmentType}=${segmentValue}: 전체 기간 이전활성:${totalPreviousActive}명, 총이탈:${totalChurned}명, 이탈률:${churnRate}%`);
        
        results.push({
            segment_value: segmentValue,
            current_active: totalCurrentActive,
            previous_active: totalPreviousActive,
            churned_users: totalChurned,
            churn_rate: Math.round(churnRate * 10) / 10,
            is_uncertain: isUncertain
        });
    });
    
    // 연령대의 경우 연령 순서로 정렬, 다른 세그먼트는 이탈률 높은 순으로 정렬
    if (segmentType === 'age_band') {
        return results.sort((a, b) => {
            const ageOrder = ['10s', '20s', '30s', '40s', '50s', '60s'];
            const aIndex = ageOrder.indexOf(a.segment_value);
            const bIndex = ageOrder.indexOf(b.segment_value);
            if (aIndex === -1 && bIndex === -1) return a.segment_value.localeCompare(b.segment_value);
            if (aIndex === -1) return 1;
            if (bIndex === -1) return -1;
            return aIndex - bIndex;
        });
    } else {
        return results.sort((a, b) => b.churn_rate - a.churn_rate);
    }
}

// 특정 타입의 세그먼트 분석 (단일 월 비교 - 기존 함수 유지)
function analyzeSegmentByType(data, segmentType, segmentValues, currentMonth, previousMonth) {
    const results = [];
    
    segmentValues.forEach(segmentValue => {
        // 해당 세그먼트의 데이터만 필터링
        const segmentData = data.filter(row => row[segmentType] === segmentValue);
        
        if (segmentData.length === 0) return;
        
        // 월별 활성 사용자 계산
        const activeUsersByMonth = {};
        segmentData.forEach(row => {
                if (!activeUsersByMonth[row.year_month]) {
                    activeUsersByMonth[row.year_month] = new Set();
                }
                activeUsersByMonth[row.year_month].add(row.user_hash);
        });
        
        const currentActive = activeUsersByMonth[currentMonth] ? activeUsersByMonth[currentMonth].size : 0;
        const previousActive = activeUsersByMonth[previousMonth] ? activeUsersByMonth[previousMonth].size : 0;
        
        if (previousActive === 0) return;
        
        // 이탈 사용자 계산
        const currentSet = activeUsersByMonth[currentMonth] || new Set();
        const previousSet = activeUsersByMonth[previousMonth] || new Set();
        const churnedUsers = [...previousSet].filter(user => !currentSet.has(user));
        const churnRate = (churnedUsers.length / previousActive) * 100;
        
        // Uncertain 판정 (모수가 적으면)
        const isUncertain = previousActive < 30;
        
        results.push({
            segment_value: segmentValue,
            current_active: currentActive,
            previous_active: previousActive,
            churned_users: churnedUsers.length,
            churn_rate: Math.round(churnRate * 10) / 10,
            is_uncertain: isUncertain
        });
    });
    
    return results.sort((a, b) => b.churn_rate - a.churn_rate);
}

// 복합 세그먼트 분석 함수
function analyzeCombinedSegment(data, startMonth, endMonth) {
    const results = [];
    
    // 분석할 월 범위 생성
    const months = generateMonthRange(startMonth, endMonth);
    if (months.length < 2) {
        console.log(`[DEBUG] 복합 세그먼트 분석: 충분한 월 데이터가 없음`);
        return [];
    }
    
    // 성별, 연령대, 채널의 모든 조합 생성
    const genders = ['M', 'F'];
    const ageBands = [...new Set(data.map(row => row.age_band).filter(age => age && age !== 'Unknown'))];
    const channels = ['web', 'app'];
    
    // 각 조합에 대해 분석
    genders.forEach(gender => {
        ageBands.forEach(ageBand => {
            channels.forEach(channel => {
                const segmentValue = `${gender}/${ageBand}/${channel}`;
                
                // 해당 조합의 데이터만 필터링
                const segmentData = data.filter(row => 
                    row.gender === gender && 
                    row.age_band === ageBand && 
                    row.channel === channel
                );
                
                if (segmentData.length === 0) return;
                
                // 월별 활성 사용자 계산
                const activeUsersByMonth = {};
                segmentData.forEach(row => {
                    if (!activeUsersByMonth[row.year_month]) {
                        activeUsersByMonth[row.year_month] = new Set();
                    }
                    activeUsersByMonth[row.year_month].add(row.user_hash);
                });
                
                let totalPreviousActive = 0;
                let totalChurned = 0;
                let totalCurrentActive = 0;
                
                // 모든 월 전환에 대해 집계
                for (let i = 1; i < months.length; i++) {
                    const previousMonth = months[i - 1];
                    const currentMonth = months[i];
                    
                    const currentSet = activeUsersByMonth[currentMonth] || new Set();
                    const previousSet = activeUsersByMonth[previousMonth] || new Set();
                    
                    if (previousSet.size > 0) {
                        totalPreviousActive += previousSet.size;
                        const churnedUsers = [...previousSet].filter(user => !currentSet.has(user));
                        totalChurned += churnedUsers.length;
                    }
                    
                    // 마지막 월의 현재 활성 사용자 수
                    if (i === months.length - 1) {
                        totalCurrentActive = currentSet.size;
                    }
                }
                
                if (totalPreviousActive === 0) return;
                
                const churnRate = (totalChurned / totalPreviousActive) * 100;
                const isUncertain = totalPreviousActive < 30;
                
                results.push({
                    segment_value: segmentValue,
                    current_active: totalCurrentActive,
                    previous_active: totalPreviousActive,
                    churned_users: totalChurned,
                    churn_rate: Math.round(churnRate * 10) / 10,
                    is_uncertain: isUncertain
                });
                
                console.log(`[DEBUG] 복합세그먼트 ${segmentValue}: 이탈률 ${churnRate.toFixed(1)}% (활성: ${totalCurrentActive}명)`);
            });
        });
    });
    
    return results.sort((a, b) => b.churn_rate - a.churn_rate);
}

// 데이터 품질 계산 (동적)
function calculateDataQuality(data) {
    if (!data || data.length === 0) {
        return {
            total_events: 0,
            invalid_events: 0,
            data_completeness: 0,
            unknown_ratio: 0
        };
    }
    
    const totalEvents = data.length;
    let unknownCount = 0;
    let invalidCount = 0;
    
    data.forEach(row => {
        // Unknown 값 카운트
        if (row.channel === 'Unknown') {
            unknownCount++;
        }
        
        // 필수 필드 누락 체크
        if (!row.user_hash || !row.created_at || !row.action) {
            invalidCount++;
        }
    });
    
    const uniqueUsers = new Set(data.map(row => row.user_hash)).size;
    
    return {
        total_events: totalEvents,
        invalid_events: invalidCount,
        data_completeness: Math.round(((totalEvents - invalidCount) / totalEvents) * 100 * 10) / 10,
        unknown_ratio: Math.round((unknownCount / totalEvents) * 100 * 10) / 10,
        unique_users: uniqueUsers
    };
}

// 동적 인사이트 생성
// [DEPRECATED] 기존 하드코딩된 인사이트 생성 - LLM으로 대체됨
function generateDynamicInsights(metrics, segmentAnalysis, chartData) {
    const inactivityThreshold = getInactiveThresholdValue();
    const insights = [];
    
    // 1. 전체 이탈률 트렌드 인사이트
    if (chartData.trendData && chartData.trendData.length >= 2) {
        const currentRate = chartData.trendData[chartData.trendData.length - 1];
        const previousRate = chartData.trendData[chartData.trendData.length - 2];
        const change = currentRate - previousRate;
        
        if (Math.abs(change) > 1) {
            const direction = change > 0 ? '상승' : '하락';
            insights.push(`이탈률이 전월 대비 ${Math.abs(change).toFixed(1)}%p ${direction}했습니다.`);
        }
    }
    
    // 2. 세그먼트별 인사이트 (성별)
    if (segmentAnalysis.gender && segmentAnalysis.gender.length >= 2) {
        const genderData = segmentAnalysis.gender;
        const highest = genderData[0];
        const lowest = genderData[genderData.length - 1];
        const diff = highest.churn_rate - lowest.churn_rate;
        
        if (diff > 3) {
            const highName = highest.segment_value === 'M' ? '남성' : '여성';
            const lowName = lowest.segment_value === 'M' ? '남성' : '여성';
            const uncertainNote = highest.is_uncertain ? ' (모수 부족으로 Uncertain 표기)' : '';
            
            insights.push(`${highName} 사용자의 이탈률이 ${lowName} 대비 ${diff.toFixed(1)}%p 높습니다${uncertainNote}.`);
        }
    }
    
    // 3. 연령대별 인사이트
    if (segmentAnalysis.age_band && segmentAnalysis.age_band.length > 0) {
        const ageData = segmentAnalysis.age_band;
        const highestAge = ageData[0];
        
        if (highestAge.churn_rate > 20) {
            const uncertainNote = highestAge.is_uncertain ? ' (모수 부족으로 Uncertain 표기)' : '';
            insights.push(`${highestAge.segment_value} 세그먼트에서 높은 이탈률(${highestAge.churn_rate}%)을 보입니다${uncertainNote}.`);
        }
    }
    
    // 4. 장기 미접속 인사이트
    if ((metrics.longTermInactive || 0) > 0 && (metrics.activeUsers || 0) > 0) {
        const inactiveRatio = (metrics.longTermInactive / ((metrics.activeUsers || 0) + metrics.longTermInactive)) * 100;
        if (inactiveRatio > 10) {
            insights.push(`⏳ ${inactivityThreshold}일 이상 미접속 사용자가 전체의 ${inactiveRatio.toFixed(1)}%입니다. 복귀 전략을 검토하세요.`);
        }
    }
    
    // 최대 3개까지만 반환
    return insights.slice(0, 3);
}

// 동적 액션 생성
// [DEPRECATED] 기존 하드코딩된 액션 생성 - LLM으로 대체됨
function generateDynamicActions(insights, segmentAnalysis, metrics) {
    const actions = [];
    
    // 1. 세그먼트별 액션
    if (segmentAnalysis.gender) {
        const femaleData = segmentAnalysis.gender.find(s => s.segment_value === 'F');
        const maleData = segmentAnalysis.gender.find(s => s.segment_value === 'M');
        
        if (femaleData && maleData && femaleData.churn_rate > maleData.churn_rate + 5) {
            actions.push('여성 사용자 대상 맞춤형 콘텐츠 및 커뮤니티 활동 강화');
        }
    }
    
    // 2. 연령대별 액션
    if (segmentAnalysis.age_band) {
        const highChurnAge = segmentAnalysis.age_band.find(s => s.churn_rate > 25);
        if (highChurnAge) {
            if (highChurnAge.segment_value.includes('50') || highChurnAge.segment_value.includes('60')) {
                actions.push('50대 이상 사용자를 위한 사용성 개선 및 신규 가이드 제공');
            } else {
                actions.push(`${highChurnAge.segment_value} 사용자를 위한 맞춤형 서비스 개선`);
            }
        }
    }
    
    // 3. 채널별 액션
    if (segmentAnalysis.channel) {
        const appData = segmentAnalysis.channel.find(s => s.segment_value === 'app');
        const webData = segmentAnalysis.channel.find(s => s.segment_value === 'web');
        
        if (appData && webData && appData.churn_rate > webData.churn_rate + 3) {
            actions.push('모바일 앱 사용자 경험 개선 및 푸시 알림 최적화');
        }
    }
    
    // 4. 일반적인 액션
    if (metrics.longTermInactive > 0) {
        actions.push('장기 미접속자 대상 복귀 유도 캠페인 및 개인화된 콘텐츠 추천');
    }
    
    // 5. 재활성 사용자 관련 액션
    if (metrics.reactivatedUsers > 0) {
        actions.push('재활성 사용자 패턴 분석을 통한 이탈 방지 전략 수립');
    }
    
    // 최대 3개까지만 반환
    return actions.slice(0, 3);
}

// 리포트를 동적 데이터로 업데이트
async function updateReportWithDynamicData() {
    // MySQL 데이터 상태 확인
    const dataStatus = await checkBackendDataStatus();
    const hasCSVData = window.csvData && window.csvData.length > 0;
    
    if (!dataStatus.has_data && !hasCSVData) {
        updateReportSection(['데이터가 없습니다.'], ['데이터를 업로드하거나 MySQL 데이터를 생성해주세요.'], { total_events: 0, invalid_events: 0, data_completeness: 0, unknown_ratio: 0 });
        return;
    }
    
    // MySQL 데이터만 있는 경우 CSV 데이터 없이도 진행
    // dataQuality는 MySQL 데이터에서는 계산 불가하므로 기본값 사용
    const dataQuality = hasCSVData ? calculateDataQuality(window.csvData) : { total_events: dataStatus.total_events || 0, invalid_events: 0, data_completeness: 100, unknown_ratio: 0 };
    
    const config = getCurrentConfig();
    
    // 실제 계산된 메트릭과 세그먼트 데이터 사용 (백엔드 또는 프론트엔드)
    let finalMetrics;
    let segmentAnalysis;
    try {
        // 먼저 백엔드 API에서 메트릭과 세그먼트 데이터 가져오기 시도
        const backendResponse = await callBackendAPI(config);
        const isBackendDataEmpty = backendResponse.error || 
            (backendResponse.churn_rate === 0 && backendResponse.active_users === 0 && 
             backendResponse.reactivated_users === 0 && backendResponse.long_term_inactive === 0);
        
        if (isBackendDataEmpty) {
            // 백엔드 실패 시 CSV 데이터가 있으면 프론트엔드 계산 사용
            if (hasCSVData) {
                finalMetrics = calculateMetrics(window.csvData, config);
                segmentAnalysis = calculateSegmentAnalysis(window.csvData, config);
                addLog('리포트: 로컬 계산된 메트릭 사용', 'info');
            } else {
                // MySQL 데이터만 있고 백엔드 실패한 경우
                addLog('리포트: 백엔드 분석 실패. 데이터 범위를 확인해주세요.', 'warning');
                finalMetrics = {
                    churnRate: 0,
                    activeUsers: 0,
                    reactivatedUsers: 0,
                    longTermInactive: 0,
                    previousActiveUsers: 0
                };
                segmentAnalysis = {};
            }
        } else {
            // 백엔드 성공 시 백엔드 메트릭과 세그먼트 데이터 사용
            finalMetrics = {
                churnRate: backendResponse.churn_rate,
                activeUsers: backendResponse.active_users,
                reactivatedUsers: backendResponse.reactivated_users,
                longTermInactive: backendResponse.long_term_inactive,
                previousActiveUsers: backendResponse.previous_active_users || 0
            };
            
            // 백엔드에서 세그먼트 분석 결과가 있으면 사용, 없으면 CSV 데이터가 있을 때만 프론트엔드 계산
            if (backendResponse.segments) {
                segmentAnalysis = backendResponse.segments;
                addLog('리포트: 백엔드 세그먼트 분석 결과 사용', 'success');
            } else if (hasCSVData) {
                segmentAnalysis = calculateSegmentAnalysis(window.csvData, config);
                addLog('리포트: 백엔드 메트릭 + 로컬 세그먼트 분석 사용', 'info');
            } else {
                segmentAnalysis = {};
                addLog('리포트: 세그먼트 분석 결과가 없습니다', 'info');
            }
            addLog('리포트: 백엔드 계산된 메트릭 사용', 'success');
        }
    } catch (error) {
        // API 호출 실패 시 CSV 데이터가 있으면 프론트엔드 계산 사용
        if (hasCSVData) {
            finalMetrics = calculateMetrics(window.csvData, config);
            segmentAnalysis = calculateSegmentAnalysis(window.csvData, config);
            addLog('리포트: API 실패로 로컬 메트릭 사용', 'warning');
        } else {
            addLog(`리포트: API 호출 실패 - ${error.message}`, 'error');
            finalMetrics = {
                churnRate: 0,
                activeUsers: 0,
                reactivatedUsers: 0,
                longTermInactive: 0,
                previousActiveUsers: 0
            };
            segmentAnalysis = {};
        }
    }
    
    console.log('[DEBUG] 리포트용 최종 메트릭:', finalMetrics);
    console.log('[DEBUG] 리포트용 세그먼트 분석:', segmentAnalysis);
    
        // 차트 데이터 계산 제거됨
    // dataQuality는 이미 위에서 계산됨
    
    // 백엔드 API 호출하여 LLM 기반 인사이트 생성 (실제 메트릭 포함)
    try {
        addLog('AI 인사이트 생성 중...', 'info');
        
        const response = await fetch('/api/churn/analysis/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                start_month: config.month || '2025-10',
                end_month: config.month || '2025-10',
                segments: {
                    channel: config.segments.channel || false,
                    action_type: config.segments.action_type || false
                },
                // 실제 계산된 메트릭 전달
                calculated_metrics: {
                    churn_rate: finalMetrics.churnRate,
                    active_users: finalMetrics.activeUsers,
                    reactivated_users: finalMetrics.reactivatedUsers,
                    long_term_inactive: finalMetrics.longTermInactive,
                    previous_active_users: finalMetrics.previousActiveUsers
                }
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            
            addLog('✅ AI 분석 완료!', 'success');
            
            // 백엔드 응답에서 세그먼트 분석 결과 사용 (우선순위 높음)
            const finalSegmentAnalysis = result.segments && Object.keys(result.segments).length > 0 
                ? result.segments 
                : segmentAnalysis;
            
            console.log('[DEBUG] 리포트 업데이트 - 세그먼트 분석 결과:', finalSegmentAnalysis);
            console.log('[DEBUG] - 세그먼트 타입:', Object.keys(finalSegmentAnalysis));
            
            updateReportSection(
                result.insights || [],
                result.actions || [],
                dataQuality,
                result.llm_metadata,
                finalSegmentAnalysis
            );
        } else {
            throw new Error(`API 호출 실패: ${response.status}`);
        }
        
    } catch (error) {
        addLog(`❌ AI 인사이트 생성 실패: ${error.message}`, 'error');
        
        // AI 실패 시 기본 분석 기반 인사이트 생성 (세그먼트 분석 결과 활용)
        const basicInsights = generateBasicInsights(finalMetrics, segmentAnalysis, null, config);
        const basicActions = generateBasicActions(finalMetrics, segmentAnalysis);
        
        const fallbackMetadata = {
            generation_method: 'basic_analysis',
            fallback_used: true,
            setup_required: false,
            error: error.message,
            timestamp: new Date().toISOString()
        };
        
        updateReportSection(basicInsights, basicActions, dataQuality, fallbackMetadata, segmentAnalysis);
    }
    
    addLog('리포트 업데이트 완료', 'success');
}

// 기본 인사이트 생성 (AI 실패 시 사용)
function generateBasicInsights(metrics, segmentAnalysis, chartData, config = {}) {
    const inactivityThreshold = 90;
    const insights = [];
    
    // 1. 전체 이탈률 인사이트
    const churnRate = metrics.churnRate || 0;
    if (churnRate > 25) {
        insights.push(`⚠️ 전체 이탈률이 ${churnRate.toFixed(1)}%로 매우 높은 수준입니다.`);
    } else if (churnRate > 15) {
        insights.push(`📊 전체 이탈률이 ${churnRate.toFixed(1)}%로 주의가 필요한 수준입니다.`);
    } else {
        insights.push(`✅ 전체 이탈률이 ${churnRate.toFixed(1)}%로 양호한 수준입니다.`);
    }
    
    // 2. 활성 사용자 인사이트
    const activeUsers = metrics.activeUsers || 0;
    const previousUsers = metrics.previousActiveUsers || 0;
    if (previousUsers > 0) {
        const growth = ((activeUsers - previousUsers) / previousUsers * 100);
        if (growth > 5) {
            insights.push(`📈 활성 사용자가 ${activeUsers.toLocaleString()}명으로 ${growth.toFixed(1)}% 증가했습니다.`);
        } else if (growth < -5) {
            insights.push(`📉 활성 사용자가 ${activeUsers.toLocaleString()}명으로 ${Math.abs(growth).toFixed(1)}% 감소했습니다.`);
        } else {
            insights.push(`📊 활성 사용자가 ${activeUsers.toLocaleString()}명으로 안정적인 수준입니다.`);
        }
    } else {
        insights.push(`👥 현재 활성 사용자는 ${activeUsers.toLocaleString()}명입니다.`);
    }
    
    // 3. 세그먼트 인사이트 (선택된 세그먼트가 있는 경우)
    if (segmentAnalysis && Object.keys(segmentAnalysis).length > 0) {
        console.log('[DEBUG] 세그먼트 분석 결과:', segmentAnalysis);
        
        // 성별 분석
        if (segmentAnalysis.gender && segmentAnalysis.gender.length >= 2) {
            const genderData = segmentAnalysis.gender;
            const highest = genderData.reduce((prev, current) => 
                (prev.churn_rate > current.churn_rate) ? prev : current
            );
            const lowest = genderData.reduce((prev, current) => 
                (prev.churn_rate < current.churn_rate) ? prev : current
            );
            
            if (Math.abs(highest.churn_rate - lowest.churn_rate) > 3) {
                const highName = highest.segment_value === 'M' ? '남성' : '여성';
                const lowName = lowest.segment_value === 'M' ? '남성' : '여성';
                const uncertainNote = highest.is_uncertain ? ' (모수 부족)' : '';
                insights.push(`👥 ${highName} 사용자의 이탈률(${highest.churn_rate.toFixed(1)}%)이 ${lowName}(${lowest.churn_rate.toFixed(1)}%) 대비 높습니다${uncertainNote}.`);
            }
        }
        
        // 연령대 분석
        if (segmentAnalysis.age_band && segmentAnalysis.age_band.length > 0) {
            const ageData = segmentAnalysis.age_band;
            const highestAge = ageData.reduce((prev, current) => 
                (prev.churn_rate > current.churn_rate) ? prev : current
            );
            
            if (highestAge.churn_rate > 20) {
                const uncertainNote = highestAge.is_uncertain ? ' (모수 부족)' : '';
                const formattedAge = formatAgeBand(highestAge.segment_value);
                insights.push(`👴 ${formattedAge} 세그먼트에서 높은 이탈률(${highestAge.churn_rate.toFixed(1)}%)을 보입니다${uncertainNote}.`);
            }
        }
        
        // 채널 분석
        if (segmentAnalysis.channel && segmentAnalysis.channel.length >= 2) {
            const channelData = segmentAnalysis.channel;
            const highest = channelData.reduce((prev, current) => 
                (prev.churn_rate > current.churn_rate) ? prev : current
            );
            const lowest = channelData.reduce((prev, current) => 
                (prev.churn_rate < current.churn_rate) ? prev : current
            );
            
            if (Math.abs(highest.churn_rate - lowest.churn_rate) > 3) {
                const highName = highest.segment_value === 'app' ? '모바일 앱' : '웹';
                const lowName = lowest.segment_value === 'app' ? '모바일 앱' : '웹';
                const uncertainNote = highest.is_uncertain ? ' (모수 부족)' : '';
                insights.push(`📱 ${highName} 사용자의 이탈률(${highest.churn_rate.toFixed(1)}%)이 ${lowName}(${lowest.churn_rate.toFixed(1)}%) 대비 높습니다${uncertainNote}.`);
            }
        }
        
        // 복합 세그먼트 분석
        if (segmentAnalysis.combined && segmentAnalysis.combined.length > 0) {
            const combinedData = segmentAnalysis.combined;
            const highestCombined = combinedData[0]; // 이미 정렬되어 있음
            
            if (highestCombined.churn_rate > 30) {
                const uncertainNote = highestCombined.is_uncertain ? ' (모수 부족)' : '';
                insights.push(`🎯 복합 세그먼트 ${highestCombined.segment_value}에서 매우 높은 이탈률(${highestCombined.churn_rate.toFixed(1)}%)을 보입니다${uncertainNote}.`);
            }
        }
    } else {
        // 세그먼트 분석이 없을 때 기본 메시지
        insights.push(`📊 세그먼트 분석을 활성화하면 더 상세한 인사이트를 얻을 수 있습니다.`);
    }
    
    // 4. 장기 미접속 사용자 인사이트
    if ((metrics.longTermInactive || 0) > 0 && (metrics.activeUsers || 0) > 0) {
        const inactiveRatio = (metrics.longTermInactive / ((metrics.activeUsers || 0) + metrics.longTermInactive)) * 100;
        if (inactiveRatio > 10) {
            insights.push(`⏳ 장기 미접속 사용자가 전체의 ${inactiveRatio.toFixed(1)}%입니다. 복귀 전략을 검토하세요.`);
        }
    }
    
    return insights.slice(0, 3); // 최대 3개
}

// 기본 액션 생성 (AI 실패 시 사용)
function generateBasicActions(metrics, segmentAnalysis) {
    const actions = [];
    
    // 1. 이탈률 기반 액션
    const churnRate = metrics.churnRate || 0;
    if (churnRate > 20) {
        actions.push("🚨 긴급 이탈 방지 프로그램 도입 및 사용자 피드백 수집");
    } else if (churnRate > 15) {
        actions.push("📋 이탈 위험 사용자 식별 및 맞춤형 리텐션 캠페인 실행");
    } else {
        actions.push("✨ 현재 서비스 품질 유지 및 사용자 만족도 지속 모니터링");
    }
    
    // 2. 세그먼트 기반 액션
    if (segmentAnalysis && Object.keys(segmentAnalysis).length > 0) {
        // 성별 세그먼트 액션
        if (segmentAnalysis.gender && segmentAnalysis.gender.length >= 2) {
            const genderData = segmentAnalysis.gender;
            const highest = genderData.reduce((prev, current) => 
                (prev.churn_rate > current.churn_rate) ? prev : current
            );
            
            if (highest.churn_rate > 15) {
                const targetGender = highest.segment_value === 'M' ? '남성' : '여성';
                actions.push(`👥 ${targetGender} 사용자 대상 맞춤형 콘텐츠 및 서비스 개선`);
            }
        }
        
        // 연령대 세그먼트 액션
        if (segmentAnalysis.age_band && segmentAnalysis.age_band.length > 0) {
            const ageData = segmentAnalysis.age_band;
            const highestAge = ageData.reduce((prev, current) => 
                (prev.churn_rate > current.churn_rate) ? prev : current
            );
            
            if (highestAge.churn_rate > 18) {
                actions.push(`🎯 ${highestAge.segment_value} 연령대를 위한 전용 서비스 및 UI/UX 개선`);
            }
        }
        
        // 채널 세그먼트 액션
        if (segmentAnalysis.channel && segmentAnalysis.channel.length >= 2) {
            const channelData = segmentAnalysis.channel;
            const highest = channelData.reduce((prev, current) => 
                (prev.churn_rate > current.churn_rate) ? prev : current
            );
            
            if (highest.churn_rate > 15) {
                const targetChannel = highest.segment_value === 'web' ? '웹' : '앱';
                actions.push(`📱 ${targetChannel} 플랫폼 사용자 경험 개선 및 기능 최적화`);
            }
        }
    }
    
    // 3. 일반적인 액션
    if ((metrics.longTermInactive || 0) > 0 && (metrics.reactivatedUsers || 0) > 0) {
        const reactivationRate = metrics.reactivatedUsers / (metrics.longTermInactive + metrics.reactivatedUsers) * 100;
        if (reactivationRate < 10) {
            actions.push("🔄 장기 미접속자 대상 복귀 유도 캠페인 및 개인화된 알림 시스템 구축");
        }
    } else if ((metrics.longTermInactive || 0) > 0) {
        actions.push("🔄 장기 미접속자 대상 복귀 유도 캠페인 및 개인화된 알림 시스템 구축");
    }
    
    return actions.slice(0, 3); // 최대 3개
}

// 계산 검증 리포트 표시
async function showVerificationReport() {
    const config = getCurrentConfig();
    const month = config.month || '2025-10';
    
    const verificationCard = document.getElementById('verificationReportCard');
    const verificationContent = document.getElementById('verificationReportContent');
    
    // 리포트 표시
    verificationCard.style.display = 'block';
    verificationContent.innerHTML = '<p class="text-muted"><i class="fas fa-spinner fa-spin"></i> 검증 리포트를 생성하는 중...</p>';
    
    try {
        const response = await fetch(`/api/churn/reports/verification/${month}?threshold=1`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const report = await response.json();
        
        // 리포트 HTML 생성
        let html = `
            <div class="verification-summary mb-4">
                <h6><i class="fas fa-info-circle"></i> 계산 요약</h6>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <tr>
                            <th>이전월 (${report.config.previous_month})</th>
                            <td>${report.summary.previous_active_count}명</td>
                        </tr>
                        <tr>
                            <th>현재월 (${report.config.month})</th>
                            <td>${report.summary.current_active_count}명</td>
                        </tr>
                        <tr>
                            <th>이탈자</th>
                            <td class="text-danger">${report.summary.churned_count}명</td>
                        </tr>
                        <tr>
                            <th>유지자</th>
                            <td class="text-success">${report.summary.retained_count}명</td>
                        </tr>
                        <tr>
                            <th>재활성</th>
                            <td class="text-info">${report.summary.reactivated_count}명</td>
                        </tr>
                        <tr class="table-primary">
                            <th>이탈률</th>
                            <td><strong>${report.summary.churn_rate}%</strong></td>
                        </tr>
                        <tr>
                            <th>유지율</th>
                            <td>${report.summary.retention_rate}%</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <div class="calculation-steps mb-4">
                <h6><i class="fas fa-list-ol"></i> 계산 단계</h6>
                <ol>
                    <li>${report.calculation_steps.step1}</li>
                    <li>${report.calculation_steps.step2}</li>
                    <li>${report.calculation_steps.step3}</li>
                    <li>${report.calculation_steps.step4}</li>
                    <li>${report.calculation_steps.step5}</li>
                    <li><strong>${report.calculation_steps.step6}</strong></li>
                </ol>
            </div>
            
            <div class="user-lists mb-4">
                <h6><i class="fas fa-users"></i> 사용자 목록</h6>
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <strong>이전월 활성 사용자 (${report.user_lists.previous_active_users.length}명):</strong>
                        <ul class="list-group list-group-flush mt-2">
                            ${report.user_lists.previous_active_users.slice(0, 20).map(u => `<li class="list-group-item py-1">${u}</li>`).join('')}
                            ${report.user_lists.previous_active_users.length > 20 ? `<li class="list-group-item py-1 text-muted">... 외 ${report.user_lists.previous_active_users.length - 20}명</li>` : ''}
                        </ul>
                    </div>
                    <div class="col-md-6 mb-3">
                        <strong>현재월 활성 사용자 (${report.user_lists.current_active_users.length}명):</strong>
                        <ul class="list-group list-group-flush mt-2">
                            ${report.user_lists.current_active_users.slice(0, 20).map(u => `<li class="list-group-item py-1">${u}</li>`).join('')}
                            ${report.user_lists.current_active_users.length > 20 ? `<li class="list-group-item py-1 text-muted">... 외 ${report.user_lists.current_active_users.length - 20}명</li>` : ''}
                        </ul>
                    </div>
                </div>
                <div class="row mt-3">
                    <div class="col-md-6 mb-3">
                        <strong class="text-danger">이탈자 (${report.user_lists.churned_users.length}명):</strong>
                        <ul class="list-group list-group-flush mt-2">
                            ${report.user_lists.churned_users.map(u => `<li class="list-group-item py-1">${u}</li>`).join('')}
                            ${report.user_lists.churned_users.length === 0 ? '<li class="list-group-item py-1 text-muted">없음</li>' : ''}
                        </ul>
                    </div>
                    <div class="col-md-6 mb-3">
                        <strong class="text-info">재활성 사용자 (${report.user_lists.reactivated_users.length}명):</strong>
                        <ul class="list-group list-group-flush mt-2">
                            ${report.user_lists.reactivated_users.map(u => `<li class="list-group-item py-1">${u}</li>`).join('')}
                            ${report.user_lists.reactivated_users.length === 0 ? '<li class="list-group-item py-1 text-muted">없음</li>' : ''}
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        verificationContent.innerHTML = html;
        addLog('검증 리포트 생성 완료', 'success');
        
        // 리포트로 스크롤
        verificationCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
    } catch (error) {
        console.error('[ERROR] 검증 리포트 생성 실패:', error);
        verificationContent.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> 검증 리포트 생성 실패: ${error.message}
            </div>
        `;
        addLog(`검증 리포트 생성 실패: ${error.message}`, 'error');
    }
}

// 리포트 섹션 업데이트 (기존 함수 개선)
function updateReportSection(insights, actions, dataQuality, llmMetadata = null, segmentAnalysis = null) {
    // 인사이트 업데이트 (신규 구조 우선: .section-block > .plain-list)
    const insightsContainer = document.querySelector('#report .section-block:nth-of-type(1) ul.plain-list')
        || document.querySelector('#report .mb-4:first-child ul');
    if (insightsContainer) {
        if (insights && insights.length > 0) {
            insightsContainer.innerHTML = insights.map((insight, index) => {
                const colors = ['var(--primary-color)', 'var(--warning-color)', 'var(--info-color)'];
                const color = colors[index] || 'var(--info-color)';
                return `<li class="mb-2">
                    <i class="fas fa-circle" style="font-size: 0.5rem; color: ${color}; margin-right: .5rem;"></i>
                    ${insight}
                </li>`;
            }).join('');
        } else {
            // 기본 메시지 표시 (데이터 부족이 아닌 분석 진행 중 메시지)
            insightsContainer.innerHTML = `
                <li class="mb-2">
                    <i class="fas fa-circle" style="font-size: 0.5rem; color: var(--info-color); margin-right: .5rem;"></i>
                    📊 데이터 분석을 진행 중입니다. 파일을 업로드하고 분석을 실행해주세요.
                </li>
                <li class="mb-2">
                    <i class="fas fa-circle" style="font-size: 0.5rem; color: var(--text-light); margin-right: .5rem;"></i>
                    🔍 분석 완료 후 실제 데이터 기반 인사이트가 표시됩니다.
                </li>
            `;
        }
    }

    // 액션 업데이트 (신규 구조 우선)
    const actionsContainer = document.querySelector('#report .section-block:nth-of-type(2) ul.plain-list')
        || document.querySelector('#report .mb-4:nth-child(2) ul');
    if (actionsContainer) {
        if (actions && actions.length > 0) {
            actionsContainer.innerHTML = actions.map(action => 
                `<li class="mb-2">
                    <i class="fas fa-arrow-right" style="color: var(--secondary-color); margin-right: .5rem;"></i>
                    ${action}
                </li>`
            ).join('');
        } else {
            // 기본 메시지 표시 (권장 액션 생성 불가가 아닌 분석 대기 메시지)
            actionsContainer.innerHTML = `
                <li class="mb-2">
                    <i class="fas fa-arrow-right" style="color: var(--primary-color); margin-right: .5rem;"></i>
                    📋 분석 완료 후 맞춤형 권장 액션이 제공됩니다.
                </li>
                <li class="mb-2">
                    <i class="fas fa-arrow-right" style="color: var(--text-light); margin-right: .5rem;"></i>
                    🎯 실제 데이터 패턴을 기반으로 한 실행 가능한 액션을 확인하세요.
                </li>
            `;
        }
    }

    // 세그먼트 분석 결과 업데이트
    if (segmentAnalysis && Object.keys(segmentAnalysis).length > 0) {
        console.log('[DEBUG] 세그먼트 분석 결과 업데이트 시작:', segmentAnalysis);
        const segmentContainer = document.querySelector('#segmentAnalysisResults ul')
            || document.querySelector('#report .section-block:nth-of-type(3) ul')
            || document.querySelector('#report .mb-4:nth-child(3) ul');
        if (segmentContainer) {
            console.log('[DEBUG] 세그먼트 컨테이너 찾음');
            let segmentHtml = '';
            
            // 성별 분석 결과
            if (segmentAnalysis.gender && segmentAnalysis.gender.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>성별 이탈률:</strong></li>';
                segmentAnalysis.gender.forEach(segment => {
                    const genderName = segment.segment_value === 'M' ? '남성' : '여성';
                    const uncertainNote = segment.is_uncertain ? ' (Uncertain)' : '';
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${genderName}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            // 연령대 분석 결과
            if (segmentAnalysis.age_band && segmentAnalysis.age_band.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>연령대별 이탈률:</strong></li>';
                segmentAnalysis.age_band.forEach(segment => {
                    const uncertainNote = segment.is_uncertain ? ' (Uncertain)' : '';
                    const formattedAge = formatAgeBand(segment.segment_value);
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${formattedAge}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            // 채널 분석 결과
            if (segmentAnalysis.channel && segmentAnalysis.channel.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>채널별 이탈률:</strong></li>';
                segmentAnalysis.channel.forEach(segment => {
                    const channelName = segment.segment_value === 'app' ? '모바일 앱' : 
                                      segment.segment_value === 'web' ? '웹' : 
                                      segment.segment_value === 'Unknown' ? '알 수 없음' : segment.segment_value;
                    const uncertainNote = segment.is_uncertain ? ' <span style="color: #ff9800; font-size: 0.9em;">(표본 적음)</span>' : '';
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${channelName}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            // 복합 세그먼트 분석 결과
            if (segmentAnalysis.combined && segmentAnalysis.combined.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>복합 세그먼트 이탈률 (성별/연령/채널):</strong></li>';
                // 상위 5개만 표시
                segmentAnalysis.combined.slice(0, 5).forEach(segment => {
                    const uncertainNote = segment.is_uncertain ? ' <span style="color: #ff9800; font-size: 0.9em;">(표본 적음)</span>' : '';
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${segment.segment_value}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            // 활동 요일 패턴 분석 결과
            if (segmentAnalysis.weekday_pattern && segmentAnalysis.weekday_pattern.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>활동 요일 패턴별 이탈률:</strong></li>';
                segmentAnalysis.weekday_pattern.forEach(segment => {
                    const patternName = segment.segment_value === '혼합' ? '기타' : segment.segment_value;
                    const uncertainNote = segment.is_uncertain ? ' <span style="color: #ff9800; font-size: 0.9em;">(표본 적음)</span>' : '';
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${patternName}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            // 활동 시간대 분석 결과
            if (segmentAnalysis.time_pattern && segmentAnalysis.time_pattern.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>활동 시간대별 이탈률:</strong></li>';
                segmentAnalysis.time_pattern.forEach(segment => {
                    const timeName = segment.segment_value === '혼합' ? '기타' : segment.segment_value;
                    const uncertainNote = segment.is_uncertain ? ' <span style="color: #ff9800; font-size: 0.9em;">(표본 적음)</span>' : '';
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${timeName}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            // 이벤트 타입별 분석 결과
            if (segmentAnalysis.action_type && segmentAnalysis.action_type.length > 0) {
                segmentHtml += '<li class="mb-2"><strong>이벤트 타입별 이탈률:</strong></li>';
                segmentAnalysis.action_type.forEach(segment => {
                    const actionName = segment.segment_value === 'view' ? '조회' :
                                     segment.segment_value === 'login' ? '로그인' :
                                     segment.segment_value === 'comment' ? '댓글' :
                                     segment.segment_value === 'like' ? '좋아요' :
                                     segment.segment_value === 'post' ? '게시글' :
                                     segment.segment_value === 'post_delete' ? '게시글 삭제' :
                                     segment.segment_value === 'post_modify' ? '게시글 수정' :
                                     segment.segment_value === 'comment_modify' ? '댓글 수정' :
                                     segment.segment_value === 'comment_delete' ? '댓글 삭제' :
                                     segment.segment_value === 'mixed' ? '기타' : segment.segment_value;
                    const uncertainNote = segment.is_uncertain ? ' <span style="color: #ff9800; font-size: 0.9em;">(표본 적음)</span>' : '';
                    const activeUsers = segment.current_active || segment.active_users || 0;
                    const churnedUsers = segment.churned_users || segment.churned || 0;
                    segmentHtml += `<li class="mb-1 ms-3">• ${actionName}: ${segment.churn_rate.toFixed(1)}% (활성: ${activeUsers}명, 이탈: ${churnedUsers}명)${uncertainNote}</li>`;
                });
            }
            
            if (segmentHtml) {
                segmentContainer.innerHTML = segmentHtml;
                console.log('[DEBUG] 세그먼트 분석 결과 HTML 업데이트 완료');
            } else {
                console.warn('[WARNING] 세그먼트 HTML이 비어있습니다');
            }
        } else {
            console.warn('[WARNING] 세그먼트 컨테이너를 찾을 수 없습니다');
        }
    } else {
        console.log('[DEBUG] 세그먼트 분석 결과가 없습니다:', segmentAnalysis);
    }

    // 데이터 품질 업데이트
    if (dataQuality) {
        const qualityContainer = document.querySelector('#report .section-block:nth-of-type(4) ul.plain-list')
            || document.querySelector('#report .mb-4:nth-child(4) ul');
        if (qualityContainer) {
            qualityContainer.innerHTML = `
                <li class="mb-1">• 총 ${dataQuality.total_events.toLocaleString()}행 검증 완료 (${dataQuality.invalid_events}행 제외)</li>
                <li class="mb-1">• 고유 사용자: ${dataQuality.unique_users ? dataQuality.unique_users.toLocaleString() : 0}명</li>
                <li class="mb-1">• 데이터 완전성: ${dataQuality.data_completeness}%</li>
                <li class="mb-1">• Unknown 값 비율: ${dataQuality.unknown_ratio}%</li>
            `;
        }
    }
}
