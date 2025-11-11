-- reasoning 컬럼 삭제 (비용 절감)
-- OpenAI Vision API 호출 시 판단 근거를 요청하지 않아 토큰 절약

ALTER TABLE image_analysis_logs
DROP COLUMN reasoning;

