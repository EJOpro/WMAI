/**
 * TrendStream SDK v1.0
 * 실제 웹사이트에 삽입하여 사용하는 이벤트 수집 스크립트
 */

(function() {
    'use strict';

    // ========================================
    // 설정
    // ========================================
    const TRENDSTREAM_CONFIG = {
        apiUrl: 'http://localhost:8000/collect',  // TODO: 실제 서버 URL로 변경
        sessionDuration: 30 * 60 * 1000, // 30분
        autoTrack: {
            pageview: true,
            click: true,
            scroll: true,
            search: true,
        }
    };

    // ========================================
    // 유틸리티 함수
    // ========================================
    
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    function generateHash(str) {
        // 간단한 해시 생성 (실제로는 서버에서 SHA-256 사용 권장)
        let hash = '';
        for (let i = 0; i < 64; i++) {
            hash += '0123456789abcdef'.charAt(Math.floor(Math.random() * 16));
        }
        return hash;
    }

    function getDeviceType() {
        const ua = navigator.userAgent;
        if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) {
            return 'tablet';
        }
        if (/Mobile|Android|iP(hone|od)|IEMobile|BlackBerry|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/.test(ua)) {
            return 'mobile';
        }
        return 'desktop';
    }

    function getCountryCode() {
        // 실제로는 서버에서 IP 기반으로 감지
        return 'KR'; // 기본값
    }

    function getUrlParam(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    function setCookie(name, value, days) {
        const expires = new Date();
        expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
        document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
    }

    // ========================================
    // 세션 관리
    // ========================================
    
    function getOrCreateSessionId() {
        let sessionId = sessionStorage.getItem('ts_session_id');
        const lastActivity = sessionStorage.getItem('ts_last_activity');
        const now = Date.now();

        if (!sessionId || !lastActivity || (now - parseInt(lastActivity) > TRENDSTREAM_CONFIG.sessionDuration)) {
            sessionId = generateUUID();
            sessionStorage.setItem('ts_session_id', sessionId);
        }

        sessionStorage.setItem('ts_last_activity', now.toString());
        return sessionId;
    }

    function getOrCreateUserId() {
        let userId = getCookie('ts_user_id');
        if (!userId) {
            userId = generateHash(navigator.userAgent + Date.now());
            setCookie('ts_user_id', userId, 365);
        }
        return userId;
    }

    // ========================================
    // 이벤트 전송
    // ========================================
    
    function sendEvent(eventType, eventData = {}) {
        const event = {
            event_time: new Date().toISOString(),
            session_id: getOrCreateSessionId(),
            user_hash: getOrCreateUserId(),
            page_path: window.location.pathname,
            utm_source: getUrlParam('utm_source'),
            utm_medium: getUrlParam('utm_medium'),
            utm_campaign: getUrlParam('utm_campaign'),
            device: getDeviceType(),
            country_iso2: getCountryCode(),
            event_type: eventType,
            event_value: Object.keys(eventData).length > 0 ? eventData : null,
            referrer: document.referrer || null
        };

        // Beacon API 사용 (페이지 이탈 시에도 전송 보장)
        if (navigator.sendBeacon) {
            const blob = new Blob([JSON.stringify({ events: [event] })], { type: 'application/json' });
            navigator.sendBeacon(TRENDSTREAM_CONFIG.apiUrl, blob);
        } else {
            // Fallback: fetch
            fetch(TRENDSTREAM_CONFIG.apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ events: [event] }),
                keepalive: true
            }).catch(err => console.error('TrendStream error:', err));
        }

        // 디버그 모드
        if (window.TrendStream && window.TrendStream.debug) {
            console.log('[TrendStream]', eventType, event);
        }
    }

    // ========================================
    // 자동 추적
    // ========================================
    
    // 페이지뷰 추적
    if (TRENDSTREAM_CONFIG.autoTrack.pageview) {
        sendEvent('pageview', {
            title: document.title,
            url: window.location.href
        });
    }

    // 클릭 추적
    if (TRENDSTREAM_CONFIG.autoTrack.click) {
        document.addEventListener('click', function(e) {
            const target = e.target.closest('a, button');
            if (target) {
                sendEvent('click', {
                    element_type: target.tagName.toLowerCase(),
                    element_id: target.id || null,
                    element_class: target.className || null,
                    element_text: target.innerText?.substring(0, 100) || null,
                    href: target.href || null
                });
            }
        });
    }

    // 스크롤 추적 (25%, 50%, 75%, 100%)
    if (TRENDSTREAM_CONFIG.autoTrack.scroll) {
        const scrollDepths = [25, 50, 75, 100];
        const triggered = {};

        window.addEventListener('scroll', function() {
            const scrollPercent = (window.scrollY + window.innerHeight) / document.documentElement.scrollHeight * 100;
            
            scrollDepths.forEach(depth => {
                if (scrollPercent >= depth && !triggered[depth]) {
                    triggered[depth] = true;
                    sendEvent('scroll', { depth: depth });
                }
            });
        });
    }

    // 검색 추적 (input[type="search"] 또는 .search-input)
    if (TRENDSTREAM_CONFIG.autoTrack.search) {
        document.addEventListener('submit', function(e) {
            const form = e.target;
            const searchInput = form.querySelector('input[type="search"], .search-input, input[name*="search"], input[name*="query"], input[name*="keyword"]');
            
            if (searchInput) {
                const keyword = searchInput.value.trim();
                if (keyword) {
                    sendEvent('search', { keyword: keyword });
                }
            }
        });
    }

    // 페이지 이탈 시 체류 시간 전송
    let pageLoadTime = Date.now();
    window.addEventListener('beforeunload', function() {
        const timeOnPage = Math.floor((Date.now() - pageLoadTime) / 1000);
        sendEvent('page_exit', { 
            time_on_page: timeOnPage,
            scroll_depth: Math.floor((window.scrollY + window.innerHeight) / document.documentElement.scrollHeight * 100)
        });
    });

    // ========================================
    // 공개 API
    // ========================================
    
    window.TrendStream = {
        // 커스텀 이벤트 전송
        track: function(eventType, eventData) {
            sendEvent(eventType, eventData);
        },

        // 전환 이벤트
        conversion: function(value, currency = 'KRW') {
            sendEvent('conversion', {
                value: value,
                currency: currency
            });
        },

        // 검색 이벤트
        search: function(keyword) {
            sendEvent('search', { keyword: keyword });
        },

        // 게시글 조회 이벤트
        viewPost: function(postId, postTitle, keywords = []) {
            sendEvent('view_post', {
                post_id: postId,
                post_title: postTitle,
                keywords: keywords
            });
        },

        // 디버그 모드 활성화
        enableDebug: function() {
            this.debug = true;
            console.log('[TrendStream] Debug mode enabled');
        },

        // 설정 업데이트
        config: function(newConfig) {
            Object.assign(TRENDSTREAM_CONFIG, newConfig);
        }
    };

    console.log('[TrendStream] SDK initialized');

})();

