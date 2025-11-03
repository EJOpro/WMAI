-- DB생성
DROP DATABASE IF EXISTS `wmai`;
CREATE DATABASE `wmai` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `wmai`;

-- 1) 유저
CREATE TABLE users (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  username   VARCHAR(100) NOT NULL,
  password   VARCHAR(255) NOT NULL,
  role       ENUM('user','admin') DEFAULT 'user',
  status     ENUM('normal','suspended','inactive') DEFAULT 'normal',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2) 게시글
CREATE TABLE board (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  title       VARCHAR(255) NOT NULL,
  content     TEXT NOT NULL,
  category    VARCHAR(100) DEFAULT 'free',
  status      ENUM('exposed','blocked','hidden','deleted') DEFAULT 'exposed',
  like_count  INT DEFAULT 0,
  view_count  INT DEFAULT 0,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_board_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_board_user_id (user_id),
  INDEX idx_board_category (category),
  INDEX idx_board_status (status),
  INDEX idx_board_created_at (created_at DESC),
  FULLTEXT INDEX ft_board_title_content (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3) 댓글 (대댓글 포함)
CREATE TABLE comment (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  board_id   INT NOT NULL,
  user_id    INT NOT NULL,
  content    TEXT NOT NULL,
  parent_id  INT DEFAULT NULL,
  status     ENUM('exposed','blocked','hidden','deleted') DEFAULT 'exposed',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_comment_board  FOREIGN KEY (board_id) REFERENCES board(id) ON DELETE CASCADE,
  CONSTRAINT fk_comment_user   FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_comment_parent FOREIGN KEY (parent_id) REFERENCES comment(id) ON DELETE CASCADE,
  INDEX idx_comment_board (board_id, created_at),
  INDEX idx_comment_parent (parent_id),
  INDEX idx_comment_user (user_id),
  INDEX idx_comment_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4) 신고
CREATE TABLE report (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  report_date     DATETIME DEFAULT CURRENT_TIMESTAMP,
  report_type     VARCHAR(50) NOT NULL,
  reported_content TEXT,
  report_reason   VARCHAR(100),
  reporter_id     INT NOT NULL,
  status          ENUM('pending','reviewing','completed','rejected') DEFAULT 'pending',
  priority        ENUM('low','normal','high','urgent') DEFAULT 'normal',
  assigned_to     INT DEFAULT NULL,
  processed_date  DATETIME DEFAULT NULL,
  processing_note TEXT DEFAULT NULL,
  post_status     ENUM('pending_review','hidden','approved','deleted') DEFAULT 'pending_review',
  post_action     ENUM('none','warn','delete','keep','block') DEFAULT 'none',
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_report_reporter FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_report_assignee FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_report_status_created (status, created_at DESC),
  INDEX idx_report_priority (priority),
  INDEX idx_report_reporter (reporter_id),
  INDEX idx_report_assignee (assigned_to),
  INDEX idx_report_type (report_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5) 신고분석
CREATE TABLE report_analysis (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  report_id  BIGINT NOT NULL,
  result     ENUM('match','partial_match','mismatch') NOT NULL,
  confidence INT CHECK (confidence BETWEEN 0 AND 100),
  analysis   TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_report_analysis_report
    FOREIGN KEY (report_id) REFERENCES report(id)
    ON DELETE CASCADE,
  INDEX idx_report_analysis_report (report_id),
  INDEX idx_report_analysis_result (result)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6) 이벤트 로그
CREATE TABLE events (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_hash  VARCHAR(255) NOT NULL,
  action     ENUM('post','post_modify','post_delete','comment','comment_modify','comment_delete','view','like','login') NOT NULL,
  channel    VARCHAR(100) DEFAULT 'Unknown',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_events_user_hash (user_hash),
  INDEX idx_events_created_at (created_at DESC),
  INDEX idx_events_action (action),
  INDEX idx_events_channel (channel),
  INDEX idx_events_composite (user_hash, created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7) 윤리모델 로그
CREATE TABLE ethics_logs (
  id               BIGINT AUTO_INCREMENT PRIMARY KEY,
  text             TEXT NOT NULL,
  score            DOUBLE NOT NULL,
  confidence       DOUBLE NOT NULL,
  spam             DOUBLE NOT NULL,
  spam_confidence  DOUBLE DEFAULT NULL,
  types            TEXT,
  ip_address       VARCHAR(50) DEFAULT NULL,
  user_agent       TEXT,
  response_time    DOUBLE DEFAULT NULL,
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ethics_created_at (created_at DESC),
  INDEX idx_ethics_score (score),
  INDEX idx_ethics_spam (spam)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;