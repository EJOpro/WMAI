-- churn_analyses 테이블의 results 컬럼을 LONGTEXT로 변경
-- 세그먼트 분석 결과 등 대용량 JSON 데이터 저장을 위해 필요

USE wmai_db;

-- results 컬럼을 LONGTEXT로 변경
ALTER TABLE churn_analyses 
MODIFY COLUMN results LONGTEXT NULL;

-- 변경 확인
SHOW COLUMNS FROM churn_analyses LIKE 'results';

