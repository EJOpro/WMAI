-- 1:1 쪽지/DM 시스템 테이블 추가
-- 작성일: 2025-11-11

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL COMMENT '발신자 ID',
    receiver_id INT NOT NULL COMMENT '수신자 ID',
    subject VARCHAR(200) COMMENT '제목',
    content TEXT NOT NULL COMMENT '메시지 내용',
    is_read BOOLEAN DEFAULT FALSE COMMENT '읽음 여부',
    parent_message_id INT NULL COMMENT '답장 시 원본 메시지 ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '전송 일시',
    read_at DATETIME NULL COMMENT '읽은 일시',
    deleted_by_sender BOOLEAN DEFAULT FALSE COMMENT '발신자가 삭제',
    deleted_by_receiver BOOLEAN DEFAULT FALSE COMMENT '수신자가 삭제',
    
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,
    
    INDEX idx_sender (sender_id),
    INDEX idx_receiver (receiver_id),
    INDEX idx_created (created_at DESC),
    INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='사용자 간 1:1 쪽지 시스템';

-- 마이그레이션 완료
SELECT 'Migration completed: messages table created' AS status;

