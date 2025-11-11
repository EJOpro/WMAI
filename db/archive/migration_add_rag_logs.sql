-- RAG 로그 테이블 추가 마이그레이션
-- 실행 방법: mysql -u [사용자명] -p [데이터베이스명] < db/migration_add_rag_logs.sql

USE wmai_db;

-- RAG 상세 로그 테이블 생성
CREATE TABLE IF NOT EXISTS ethics_rag_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ethics_log_id BIGINT NOT NULL,
  
  -- 유사 케이스 정보
  similar_case_count INT DEFAULT 0 COMMENT '검색된 유사 케이스 개수',
  max_similarity DOUBLE DEFAULT NULL COMMENT '최대 유사도 점수 (0-1)',
  
  -- 보정 전후 점수
  original_immoral_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 전 비윤리 점수',
  original_spam_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 전 스팸 점수',
  adjusted_immoral_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 후 비윤리 점수',
  adjusted_spam_score DOUBLE DEFAULT NULL COMMENT 'RAG 보정 후 스팸 점수',
  
  -- 보정 메타데이터
  adjustment_weight DOUBLE DEFAULT NULL COMMENT '보정 가중치 (0-1)',
  confidence_boost DOUBLE DEFAULT NULL COMMENT '신뢰도 증가량',
  adjustment_method VARCHAR(50) DEFAULT 'similarity_based' COMMENT '보정 방법',
  
  -- 유사 케이스 상세 정보 (JSON)
  similar_cases JSON DEFAULT NULL COMMENT '유사 케이스 상세 정보',
  
  -- RAG 처리 시간 및 성능
  rag_response_time DOUBLE DEFAULT NULL COMMENT 'RAG 처리 시간 (초)',
  vector_search_time DOUBLE DEFAULT NULL COMMENT '벡터 검색 시간 (초)',
  
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  CONSTRAINT fk_rag_ethics_log 
    FOREIGN KEY (ethics_log_id) 
    REFERENCES ethics_logs(id) 
    ON DELETE CASCADE,
    
  INDEX idx_rag_ethics_log (ethics_log_id),
  INDEX idx_rag_created_at (created_at DESC),
  INDEX idx_rag_similarity (max_similarity),
  INDEX idx_rag_case_count (similar_case_count)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='RAG(Retrieval Augmented Generation) 보정 상세 로그';

-- 완료 메시지
SELECT 'ethics_rag_logs 테이블이 성공적으로 생성되었습니다.' AS message;

