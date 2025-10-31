"""이벤트 인제스트 서비스"""
from sqlalchemy import text
from typing import List, Tuple, Optional
from datetime import datetime
import json
from backend.models.schemas import EventSchema
from backend.services.database import get_write_session


class IngestService:
    """이벤트 수집 및 저장 서비스"""
    
    def _upsert_dimension_page(self, session, page_path: str) -> int:
        """페이지 차원 upsert"""
        result = session.execute(
            text("""
                INSERT INTO dim_page (page_path)
                VALUES (:page_path)
                ON DUPLICATE KEY UPDATE page_id=LAST_INSERT_ID(page_id)
            """),
            {"page_path": page_path}
        )
        session.flush()
        return result.lastrowid or session.execute(
            text("SELECT page_id FROM dim_page WHERE page_path = :page_path"),
            {"page_path": page_path}
        ).scalar()
    
    def _upsert_dimension_utm(
        self, 
        session, 
        utm_source: Optional[str], 
        utm_medium: Optional[str], 
        utm_campaign: Optional[str]
    ) -> Optional[int]:
        """UTM 차원 upsert"""
        if not utm_source and not utm_medium and not utm_campaign:
            return None
        
        result = session.execute(
            text("""
                INSERT INTO dim_utm (utm_source, utm_medium, utm_campaign)
                VALUES (:utm_source, :utm_medium, :utm_campaign)
                ON DUPLICATE KEY UPDATE utm_id=LAST_INSERT_ID(utm_id)
            """),
            {
                "utm_source": utm_source,
                "utm_medium": utm_medium,
                "utm_campaign": utm_campaign
            }
        )
        session.flush()
        return result.lastrowid
    
    def _get_device_id(self, device: str) -> int:
        """디바이스 ID 조회 (사전 정의)"""
        device_map = {
            "desktop": 1,
            "mobile": 2,
            "tablet": 3
        }
        return device_map.get(device.lower(), 1)
    
    def _upsert_dimension_country(self, session, country_iso2: str) -> int:
        """국가 차원 upsert"""
        result = session.execute(
            text("""
                INSERT INTO dim_country (country_iso2)
                VALUES (:country_iso2)
                ON DUPLICATE KEY UPDATE country_id=LAST_INSERT_ID(country_id)
            """),
            {"country_iso2": country_iso2.upper()}
        )
        session.flush()
        return result.lastrowid or session.execute(
            text("SELECT country_id FROM dim_country WHERE country_iso2 = :country_iso2"),
            {"country_iso2": country_iso2.upper()}
        ).scalar()
    
    def ingest_events(self, events: List[EventSchema]) -> Tuple[int, List[str]]:
        """
        이벤트 배치 인제스트
        
        Returns:
            (성공 건수, 에러 목록)
        """
        success_count = 0
        errors = []
        
        with get_write_session() as session:
            for idx, event in enumerate(events):
                try:
                    # 차원 테이블 upsert
                    page_id = self._upsert_dimension_page(session, event.page_path)
                    utm_id = self._upsert_dimension_utm(
                        session, 
                        event.utm_source, 
                        event.utm_medium, 
                        event.utm_campaign
                    )
                    device_id = self._get_device_id(event.device)
                    country_id = self._upsert_dimension_country(session, event.country_iso2)
                    
                    # 팩트 테이블 삽입
                    session.execute(
                        text("""
                            INSERT INTO fact_events (
                                event_time, session_id, user_hash, page_id, utm_id,
                                device_id, country_id, event_type, event_value, referrer
                            ) VALUES (
                                :event_time, :session_id, :user_hash, :page_id, :utm_id,
                                :device_id, :country_id, :event_type, :event_value, :referrer
                            )
                        """),
                        {
                            "event_time": event.event_time,
                            "session_id": event.session_id,
                            "user_hash": event.user_hash,
                            "page_id": page_id,
                            "utm_id": utm_id,
                            "device_id": device_id,
                            "country_id": country_id,
                            "event_type": event.event_type,
                            "event_value": json.dumps(event.event_value) if event.event_value else None,
                            "referrer": event.referrer
                        }
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Event {idx}: {str(e)}")
                    continue
        
        return success_count, errors


# 싱글톤 인스턴스
ingest_service = IngestService()

