document.addEventListener('DOMContentLoaded', function() {
    // DOM 요소들
    const postContent = document.getElementById('postContent');
    const reportReason = document.getElementById('reportReason');
    const reasonDescription = document.getElementById('reasonDescription');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultSection = document.getElementById('resultSection');
    const resultCard = document.getElementById('resultCard');
    const progressBar = document.getElementById('progressBar');
    const examplesSection = document.getElementById('examplesSection');
    const loadingModal = document.getElementById('loadingModal')._modalInstance;

    // 신고 사유 설명 - Streamlit과 동일
    const reasonDescriptions = {
        "욕설 및 비방": "📌 타인을 모욕하거나 명예를 훼손하는 내용",
        "도배 및 광고": "📌 반복적인 게시물이나 상업적 광고 내용",
        "사생활 침해": "📌 개인정보 노출이나 사생활을 침해하는 내용",
        "저작권 침해": "📌 타인의 저작물을 무단으로 사용한 내용"
    };

    // 신고 사유 변경 시 설명 업데이트
    reportReason.addEventListener('change', function() {
        reasonDescription.innerHTML = reasonDescriptions[this.value];
    });

    // 분석 버튼 클릭 이벤트
    analyzeBtn.addEventListener('click', async function() {
        const post = postContent.value.trim();
        const reason = reportReason.value;

        if (!post) {
            alert('게시글 내용을 입력해주세요.');
            postContent.focus();
            return;
        }

        // 로딩 모달 표시
        loadingModal.show();

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    post_content: post,
                    reason: reason
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '서버 오류가 발생했습니다.');
            }

            const result = await response.json();
            displayResult(result);

        } catch (error) {
            showError(error.message);
        } finally {
            loadingModal.hide();
        }
    });

    // 결과 표시 함수 - Streamlit 스타일과 동일
    function displayResult(result) {
        let icon = '';
        let statusMessage = '';
        
        switch(result.result_type) {
            case '일치':
                icon = '✅';
                statusMessage = '🔴 <strong>신고 내용과 일치</strong>: 게시글이 자동으로 삭제되었습니다.';
                break;
            case '불일치':
                icon = '❌';
                statusMessage = '🟢 <strong>신고 내용과 불일치</strong>: 게시글이 유지됩니다.';
                break;
            case '부분일치':
                icon = '⚠️';
                statusMessage = '🟡 <strong>부분일치 - 관리자 검토 필요</strong>: 관리자가 승인/반려를 결정합니다.';
                break;
        }

        resultCard.className = `result-card ${result.css_class}`;
        resultCard.innerHTML = `
            <h3>${icon} 판단 결과: ${result.result_type}</h3>
            <div class="confidence-score">📈 신뢰도: ${result.score}%</div>
            <p>${result.analysis}</p>
            <hr>
            <div class="alert alert-${getAlertClass(result.result_type)} mt-3">
                ${statusMessage}
            </div>
            <small class="text-muted">
                📝 신고 ID ${result.id}번으로 관리 페이지에 저장되었습니다. | 
                처리 시간: ${new Date(result.timestamp).toLocaleString('ko-KR')}
            </small>
        `;

        // 프로그레스 바 업데이트
        progressBar.style.width = result.score + '%';
        progressBar.setAttribute('aria-valuenow', result.score);
        progressBar.textContent = result.score + '%';

        // 결과 섹션 표시 및 스크롤
        resultSection.style.display = 'block';
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 알림 클래스 결정
    function getAlertClass(resultType) {
        switch(resultType) {
            case '일치': return 'success';
            case '불일치': return 'success';
            case '부분일치': return 'warning';
            default: return 'info';
        }
    }

    // 오류 표시 함수
    function showError(message) {
        resultCard.className = 'result-card result-mismatch';
        resultCard.innerHTML = `
            <h4>❌ 오류 발생</h4>
            <p>${message}</p>
        `;
        
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.textContent = '';
        
        resultSection.style.display = 'block';
        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    // 예시 데이터 로드
    async function loadExamples() {
        try {
            const response = await fetch('/api/examples');
            const examples = await response.json();

            let examplesHTML = '';
            for (const [key, example] of Object.entries(examples)) {
                examplesHTML += `
                    <div class="col-md-3 col-sm-6 mb-3">
                        <div class="example-card" onclick="useExample('${escapeHtml(example.post)}', '${example.reason}')">
                            <h6>예시 ${key}</h6>
                            <span class="badge bg-secondary mb-2">${example.reason}</span>
                            <p>${example.post.substring(0, 80)}...</p>
                            <small>클릭하여 사용하기</small>
                        </div>
                    </div>
                `;
            }
            examplesSection.innerHTML = examplesHTML;

        } catch (error) {
            console.error('예시 데이터 로드 실패:', error);
            examplesSection.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-warning">
                        예시 데이터를 불러오는데 실패했습니다.
                    </div>
                </div>
            `;
        }
    }

    // HTML 이스케이프 함수
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function(m) { return map[m]; });
    }

    // 예시 데이터 사용 함수 - Streamlit 동작과 동일
    window.useExample = function(post, reason) {
        // HTML 디코딩
        const textarea = document.createElement('textarea');
        textarea.innerHTML = post;
        const decodedPost = textarea.value;
        
        postContent.value = decodedPost;
        reportReason.value = reason;
        reasonDescription.innerHTML = reasonDescriptions[reason];
        
        // 입력 필드로 스크롤
        postContent.scrollIntoView({ behavior: 'smooth', block: 'center' });
        postContent.focus();
    };

    // Enter 키로 분석 실행 (Ctrl+Enter)
    postContent.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            analyzeBtn.click();
        }
    });

    // 입력 필드 실시간 검증
    postContent.addEventListener('input', function() {
        const hasContent = this.value.trim().length > 0;
        analyzeBtn.disabled = !hasContent;
        
        if (hasContent) {
            analyzeBtn.classList.remove('btn-secondary');
            analyzeBtn.classList.add('btn-primary');
        } else {
            analyzeBtn.classList.remove('btn-primary');
            analyzeBtn.classList.add('btn-secondary');
        }
    });

    // 초기 버튼 상태 설정
    analyzeBtn.disabled = true;
    analyzeBtn.classList.add('btn-secondary');
    analyzeBtn.classList.remove('btn-primary');

    // 페이지 로드 시 예시 데이터 로드
    loadExamples();

    // 키보드 단축키 안내
    const shortcutInfo = document.createElement('small');
    shortcutInfo.className = 'text-muted mt-2 d-block';
    shortcutInfo.innerHTML = '💡 <strong>팁:</strong> Ctrl+Enter로 빠른 분석이 가능합니다.';
    postContent.parentNode.appendChild(shortcutInfo);
});
