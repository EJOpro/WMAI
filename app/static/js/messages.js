/**
 * 메시지 시스템 JavaScript
 * 1:1 DM 기능 (CRUD, 실시간 알림)
 */

const Messages = {
    currentTab: 'inbox',
    currentPage: { inbox: 1, sent: 1 },
    currentMessageId: null,
    selectedReceiver: null,
    pollingInterval: null,

    // 초기화
    init() {
        this.attachEventListeners();
        this.loadMessages('inbox');
        this.startPolling();
    },

    // 이벤트 리스너 등록
    attachEventListeners() {
        // 탭 전환
        document.querySelectorAll('.message-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // 새 메시지 버튼
        document.getElementById('newMessageBtn').addEventListener('click', () => {
            this.openNewMessageModal();
        });

        // 새 메시지 모달 닫기
        document.getElementById('closeNewMessageModal').addEventListener('click', () => {
            this.closeNewMessageModal();
        });
        document.getElementById('cancelNewMessageBtn').addEventListener('click', () => {
            this.closeNewMessageModal();
        });

        // 메시지 전송
        document.getElementById('sendMessageBtn').addEventListener('click', () => {
            this.sendMessage();
        });

        // 수신자 검색
        const receiverInput = document.getElementById('receiverInput');
        receiverInput.addEventListener('input', (e) => {
            this.searchUsers(e.target.value);
        });

        // 내용 길이 카운터
        document.getElementById('contentInput').addEventListener('input', (e) => {
            document.getElementById('contentLength').textContent = e.target.value.length;
        });

        // 상세 모달 닫기
        document.getElementById('closeDetailModal').addEventListener('click', () => {
            this.closeDetailModal();
        });
        document.getElementById('closeDetailBtn').addEventListener('click', () => {
            this.closeDetailModal();
        });

        // 답장 버튼
        document.getElementById('replyBtn').addEventListener('click', () => {
            this.replyToMessage();
        });

        // 삭제 버튼
        document.getElementById('deleteBtn').addEventListener('click', () => {
            this.deleteMessage();
        });

        // 페이지네이션 - 받은 메시지
        document.getElementById('inboxPrevPage').addEventListener('click', () => {
            if (this.currentPage.inbox > 1) {
                this.currentPage.inbox--;
                this.loadMessages('inbox');
            }
        });
        document.getElementById('inboxNextPage').addEventListener('click', () => {
            this.currentPage.inbox++;
            this.loadMessages('inbox');
        });

        // 페이지네이션 - 보낸 메시지
        document.getElementById('sentPrevPage').addEventListener('click', () => {
            if (this.currentPage.sent > 1) {
                this.currentPage.sent--;
                this.loadMessages('sent');
            }
        });
        document.getElementById('sentNextPage').addEventListener('click', () => {
            this.currentPage.sent++;
            this.loadMessages('sent');
        });

        // 모달 외부 클릭 시 닫기
        document.getElementById('messageDetailModal').addEventListener('click', (e) => {
            if (e.target.id === 'messageDetailModal') {
                this.closeDetailModal();
            }
        });
        document.getElementById('newMessageModal').addEventListener('click', (e) => {
            if (e.target.id === 'newMessageModal') {
                this.closeNewMessageModal();
            }
        });
    },

    // 탭 전환
    switchTab(tabName) {
        this.currentTab = tabName;

        // 탭 버튼 활성화
        document.querySelectorAll('.message-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 탭 콘텐츠 표시
        document.querySelectorAll('.message-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');

        // 메시지 로드
        this.loadMessages(tabName);
    },

    // 메시지 목록 로드
    async loadMessages(type) {
        const page = this.currentPage[type];
        const tbody = document.getElementById(`${type}TableBody`);
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">불러오는 중...</td></tr>';

        try {
            const response = await fetch(`/api/messages/${type}?page=${page}&limit=20`);
            const data = await response.json();

            if (response.ok) {
                this.renderMessages(type, data.messages);
                this.updatePagination(type, data.pagination);
                
                // 개수 업데이트
                document.getElementById(`${type}Count`).textContent = data.pagination.total;
            } else {
                throw new Error(data.detail || '메시지 로드 실패');
            }
        } catch (error) {
            console.error('메시지 로드 오류:', error);
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">메시지를 불러올 수 없습니다: ${error.message}</td></tr>`;
        }
    },

    // 메시지 목록 렌더링
    renderMessages(type, messages) {
        const tbody = document.getElementById(`${type}TableBody`);

        if (!messages || messages.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">메시지가 없습니다</td></tr>';
            return;
        }

        tbody.innerHTML = messages.map(msg => {
            const isUnread = type === 'inbox' && !msg.is_read;
            const rowClass = isUnread ? 'message-unread' : '';
            const unreadIcon = isUnread ? '<i class="fas fa-envelope"></i>' : '<i class="far fa-envelope-open"></i>';
            const otherUser = type === 'inbox' ? msg.sender_username : msg.receiver_username;
            const subject = msg.subject || '(제목 없음)';
            const time = this.formatDateTime(msg.created_at);

            return `
                <tr class="${rowClass}" onclick="Messages.viewMessage(${msg.id})" style="cursor: pointer;">
                    <td class="text-center">${unreadIcon}</td>
                    <td><strong>${otherUser}</strong></td>
                    <td>${this.escapeHtml(subject)}</td>
                    <td>${time}</td>
                </tr>
            `;
        }).join('');
    },

    // 페이지네이션 업데이트
    updatePagination(type, pagination) {
        const { page, total_pages } = pagination;

        document.getElementById(`${type}PageInfo`).textContent = `${page} / ${total_pages}`;
        document.getElementById(`${type}PrevPage`).disabled = page <= 1;
        document.getElementById(`${type}NextPage`).disabled = page >= total_pages;
    },

    // 메시지 상세 보기
    async viewMessage(messageId) {
        this.currentMessageId = messageId;
        this.showLoading();

        try {
            const response = await fetch(`/api/messages/${messageId}`);
            const data = await response.json();

            if (response.ok) {
                this.renderMessageDetail(data.message);
                this.showDetailModal();
                
                // 받은 메시지함 새로고침 (읽음 처리 반영)
                if (this.currentTab === 'inbox') {
                    setTimeout(() => this.loadMessages('inbox'), 500);
                }
            } else {
                throw new Error(data.detail || '메시지 로드 실패');
            }
        } catch (error) {
            console.error('메시지 상세 로드 오류:', error);
            alert(`메시지를 불러올 수 없습니다: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    },

    // 메시지 상세 렌더링
    renderMessageDetail(message) {
        document.getElementById('messageDetailSubject').textContent = message.subject || '(제목 없음)';
        document.getElementById('detailSender').textContent = message.sender_username;
        document.getElementById('detailReceiver').textContent = message.receiver_username;
        document.getElementById('detailTime').textContent = this.formatDateTime(message.created_at);
        
        // 읽은 시간 표시
        if (message.read_at) {
            document.getElementById('detailReadTime').textContent = this.formatDateTime(message.read_at);
            document.getElementById('detailReadTimeContainer').style.display = 'block';
        } else {
            document.getElementById('detailReadTimeContainer').style.display = 'none';
        }

        // 내용 표시 (이미 HTML 이스케이프 처리됨)
        document.getElementById('messageDetailContent').innerHTML = message.content.replace(/\n/g, '<br>');

        // 답장 버튼 표시 여부 (받은 메시지함에서만)
        const currentUser = this.getCurrentUsername();
        if (message.receiver_username === currentUser) {
            document.getElementById('replyBtn').style.display = 'inline-block';
        } else {
            document.getElementById('replyBtn').style.display = 'none';
        }
    },

    // 새 메시지 모달 열기
    openNewMessageModal(receiver = null, subject = null) {
        document.getElementById('newMessageForm').reset();
        document.getElementById('contentLength').textContent = '0';
        document.getElementById('userSearchResults').innerHTML = '';
        
        if (receiver) {
            document.getElementById('receiverInput').value = receiver;
            this.selectedReceiver = receiver;
        } else {
            this.selectedReceiver = null;
        }
        
        if (subject) {
            document.getElementById('subjectInput').value = subject;
        }

        document.getElementById('newMessageModal').classList.add('show');
    },

    // 새 메시지 모달 닫기
    closeNewMessageModal() {
        document.getElementById('newMessageModal').classList.remove('show');
        this.selectedReceiver = null;
    },

    // 상세 모달 열기
    showDetailModal() {
        document.getElementById('messageDetailModal').classList.add('show');
    },

    // 상세 모달 닫기
    closeDetailModal() {
        document.getElementById('messageDetailModal').classList.remove('show');
        this.currentMessageId = null;
    },

    // 사용자 검색
    async searchUsers(query) {
        const resultsDiv = document.getElementById('userSearchResults');

        if (!query || query.trim().length < 1) {
            resultsDiv.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/api/messages/users/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (response.ok && data.users.length > 0) {
                resultsDiv.innerHTML = data.users.map(user => `
                    <div class="search-result-item" onclick="Messages.selectUser('${user.username}')">
                        <i class="fas fa-user"></i> ${user.username}
                    </div>
                `).join('');
            } else {
                resultsDiv.innerHTML = '<div class="search-result-item text-muted">검색 결과 없음</div>';
            }
        } catch (error) {
            console.error('사용자 검색 오류:', error);
            resultsDiv.innerHTML = '';
        }
    },

    // 사용자 선택
    selectUser(username) {
        document.getElementById('receiverInput').value = username;
        this.selectedReceiver = username;
        document.getElementById('userSearchResults').innerHTML = '';
    },

    // 메시지 전송
    async sendMessage() {
        const receiver = document.getElementById('receiverInput').value.trim();
        const subject = document.getElementById('subjectInput').value.trim();
        const content = document.getElementById('contentInput').value.trim();

        if (!receiver) {
            alert('받는 사람을 입력하세요.');
            return;
        }

        if (!content) {
            alert('메시지 내용을 입력하세요.');
            return;
        }

        this.showLoading();

        try {
            const response = await fetch('/api/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    receiver_username: receiver,
                    subject: subject || null,
                    content: content
                })
            });

            const data = await response.json();

            if (response.ok) {
                alert('메시지가 전송되었습니다!');
                this.closeNewMessageModal();
                this.switchTab('sent');
            } else {
                throw new Error(data.detail || '메시지 전송 실패');
            }
        } catch (error) {
            console.error('메시지 전송 오류:', error);
            alert(`메시지 전송 실패: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    },

    // 답장
    async replyToMessage() {
        if (!this.currentMessageId) return;

        this.showLoading();

        try {
            const response = await fetch(`/api/messages/${this.currentMessageId}`);
            const data = await response.json();

            if (response.ok) {
                const message = data.message;
                const replySubject = message.subject || '(제목 없음)';
                
                this.closeDetailModal();
                this.openNewMessageModal(message.sender_username, replySubject.startsWith('Re: ') ? replySubject : `Re: ${replySubject}`);
            } else {
                throw new Error(data.detail || '원본 메시지 로드 실패');
            }
        } catch (error) {
            console.error('답장 오류:', error);
            alert(`답장 실패: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    },

    // 메시지 삭제
    async deleteMessage() {
        if (!this.currentMessageId) return;

        if (!confirm('이 메시지를 삭제하시겠습니까?')) {
            return;
        }

        this.showLoading();

        try {
            const response = await fetch(`/api/messages/${this.currentMessageId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok) {
                alert('메시지가 삭제되었습니다.');
                this.closeDetailModal();
                this.loadMessages(this.currentTab);
            } else {
                throw new Error(data.detail || '메시지 삭제 실패');
            }
        } catch (error) {
            console.error('메시지 삭제 오류:', error);
            alert(`메시지 삭제 실패: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    },

    // 안읽은 메시지 개수 조회
    async getUnreadCount() {
        try {
            const response = await fetch('/api/messages/unread-count');
            const data = await response.json();

            if (response.ok) {
                this.updateUnreadBadge(data.count);
            }
        } catch (error) {
            console.error('안읽은 메시지 조회 오류:', error);
        }
    },

    // 안읽은 메시지 뱃지 업데이트
    updateUnreadBadge(count) {
        const badge = document.getElementById('messagesBadge');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    },

    // 폴링 시작 (10초마다)
    startPolling() {
        this.getUnreadCount(); // 즉시 실행
        this.pollingInterval = setInterval(() => {
            this.getUnreadCount();
        }, 10000);
    },

    // 폴링 중지
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    },

    // 현재 사용자명 가져오기 (간단한 방법)
    getCurrentUsername() {
        // 실제 구현에서는 세션에서 가져오는 것이 좋음
        // 여기서는 간단히 DOM에서 추출
        return 'current_user'; // TODO: 실제 구현 필요
    },

    // 날짜 포맷팅
    formatDateTime(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        const diffDays = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (diffDays === 0) {
            // 오늘
            return date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays === 1) {
            // 어제
            return '어제 ' + date.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
        } else if (diffDays < 7) {
            // 일주일 이내
            return `${diffDays}일 전`;
        } else {
            // 그 이전
            return date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' });
        }
    },

    // HTML 이스케이프
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // 로딩 표시
    showLoading() {
        document.getElementById('loadingOverlay').style.display = 'flex';
    },

    // 로딩 숨김
    hideLoading() {
        document.getElementById('loadingOverlay').style.display = 'none';
    }
};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    Messages.init();
});

// 페이지 언로드 시 폴링 중지
window.addEventListener('beforeunload', () => {
    Messages.stopPolling();
});

