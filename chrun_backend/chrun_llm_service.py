"""
LLM 기반 인사이트 및 권장 액션 생성 서비스
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import openai
from openai import OpenAI
import logging
import pathlib
from dotenv import load_dotenv

# 환경 변수 로드 (chrun_backend 폴더의 .env 파일 우선 로드)
current_dir = pathlib.Path(__file__).parent
env_path = current_dir / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] LLM 서비스: .env 파일 로드됨: {env_path}")
else:
    load_dotenv()  # 프로젝트 루트의 .env 파일 시도
    print("[INFO] LLM 서비스: 프로젝트 루트의 .env 파일 로드 시도")

# 로거 설정
logger = logging.getLogger(__name__)

class LLMInsightGenerator:
    """LLM을 활용한 이탈 분석 인사이트 생성기"""
    
    def __init__(self):
        self.client = None
        self.model = "gpt-4o-mini"  # 기본 모델 (캐시 키에 사용)
        self.prompt_version = "v1"  # 프롬프트 버전 (캐시 키에 사용)
        self._initialize_client()
    
    def _initialize_client(self):
        """OpenAI 클라이언트 초기화"""
        api_key = os.getenv('OPENAI_API_KEY')
        
        # 디버깅 정보
        print(f"[DEBUG] OPENAI_API_KEY 확인: {'설정됨' if api_key else '설정되지 않음'}")
        if api_key:
            print(f"[DEBUG] API 키 앞 10자리: {api_key[:10]}...")
        
        if not api_key:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다. LLM 기능이 비활성화됩니다.")
            print("[WARNING] OPENAI_API_KEY가 설정되지 않았습니다. LLM 기능이 비활성화됩니다.")
            print("[INFO] AI 인사이트를 사용하려면 OPENAI_SETUP_GUIDE.md를 참조하세요.")
            return
        
        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI 클라이언트 초기화 완료")
            print("[INFO] OpenAI 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
            print(f"[ERROR] OpenAI 클라이언트 초기화 실패: {e}")
    
    def generate_insights_and_actions(self, analysis_data: Dict) -> Dict[str, List[str]]:
        """
        분석 데이터를 바탕으로 LLM을 통해 인사이트와 권장 액션 생성
        
        Args:
            analysis_data: 이탈 분석 결과 데이터
            
        Returns:
            Dict containing 'insights' and 'actions' lists
        """
        print(f"[DEBUG] LLM generate_insights_and_actions 호출됨")
        print(f"[DEBUG] OpenAI 클라이언트 상태: {'초기화됨' if self.client else '초기화되지 않음'}")
        
        if not self.client:
            logger.warning("OpenAI 클라이언트가 초기화되지 않았습니다. 기본 인사이트를 반환합니다.")
            print("[WARNING] OpenAI 클라이언트가 없습니다. Fallback 인사이트 생성 중...")
            return self._generate_fallback_insights(analysis_data)
        
        try:
            print("[INFO] LLM 인사이트 생성 시작 - 데이터 요약 생성 중...")
            # 데이터 요약 생성
            data_summary = self._create_data_summary(analysis_data)
            print(f"[INFO] 데이터 요약 생성 완료 - 세그먼트: {len(data_summary.get('세그먼트_분석', {}))}개")
            
            # LLM 프롬프트 생성
            prompt = self._create_analysis_prompt(data_summary)
            print(f"[INFO] 프롬프트 생성 완료 - 길이: {len(prompt)}자")
            
            # OpenAI API 호출
            print("[INFO] OpenAI API 호출 중...")
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 비용 효율적인 모델 사용
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1500
            )
            
            # 응답 파싱
            print("[INFO] OpenAI API 응답 수신 - 파싱 중...")
            result = json.loads(response.choices[0].message.content)
            print(f"[INFO] 파싱 완료 - insights: {len(result.get('insights', []))}개, actions: {len(result.get('actions', []))}개")
            
            # 결과 검증 및 정제
            insights = result.get('insights', [])[:3]  # 최대 3개
            actions = result.get('actions', [])[:3]    # 최대 3개
            
            # 응답 필터링 및 검증
            insights = self._filter_and_validate_responses(insights, 'insights')
            actions = self._filter_and_validate_responses(actions, 'actions')
            
            print(f"[INFO] 필터링 완료 - 최종 insights: {len(insights)}개, actions: {len(actions)}개")
            logger.info(f"LLM 인사이트 생성 완료: {len(insights)}개 인사이트, {len(actions)}개 액션")
            
            return {
                'insights': insights,
                'actions': actions,
                'generated_by': 'llm',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"LLM 인사이트 생성 중 오류: {e}")
            return self._generate_fallback_insights(analysis_data)
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 정의"""
        return """당신은 사용자 이탈 분석 전문가입니다. 
주어진 데이터를 분석하여 실용적이고 구체적인 인사이트와 권장 액션을 제공해야 합니다.

응답 규칙:
1. JSON 형식으로만 응답하세요: {"insights": [...], "actions": [...]}
2. 인사이트는 데이터에서 발견된 중요한 패턴이나 트렌드를 설명
3. 권장 액션은 구체적이고 실행 가능한 개선 방안을 제시
4. 각각 최대 3개까지만 제공
5. 한국어로 작성하며, 반드시 존댓말을 사용하세요
6. 데이터가 부족하거나 불확실한 경우 "Uncertain" 표기
7. 통계적으로 의미 있는 차이(5%p 이상)만 언급

분석 관점:
- 세그먼트별 이탈률 차이
- 시간별 트렌드 변화
- 재활성화 패턴
- 위험 사용자 그룹
- 데이터 품질 이슈

절대 하지 말아야 할 것들:
- 추측이나 가정에 기반한 분석 금지
- 데이터에 없는 정보를 임의로 추가하지 말 것
- 개인정보나 민감한 정보 언급 금지
- 비윤리적이거나 차별적인 권장사항 제시 금지
- 법적 조언이나 의료적 조언 제공 금지
- 마케팅이나 영업 목적의 과장된 표현 사용 금지
- 선택되지 않은 세그먼트에 대한 분석 결과 언급 금지
- 통계적으로 유의미하지 않은 차이를 과장하여 설명 금지
- 불확실한 데이터를 확실한 것처럼 표현 금지"""

    def _convert_decimal(self, value):
        """Decimal 타입을 JSON 직렬화 가능한 타입으로 변환"""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, (int, float)):
            return value
        elif value is None:
            return 0
        else:
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
    
    def _create_data_summary(self, analysis_data: Dict) -> Dict:
        """분석 데이터를 LLM이 이해하기 쉬운 형태로 요약"""
        
        summary = {
            "기본_지표": {},
            "세그먼트_분석": {},
            "트렌드_분석": {},
            "데이터_품질": {},
            "선택된_세그먼트": {}
        }
        
        # 기본 지표 요약
        metrics = analysis_data.get('metrics', {})
        churn_rate = self._convert_decimal(metrics.get('churn_rate', 0))
        active_users = int(self._convert_decimal(metrics.get('active_users', 0)))
        reactivated_users = int(self._convert_decimal(metrics.get('reactivated_users', 0)))
        long_term_inactive = int(self._convert_decimal(metrics.get('long_term_inactive', 0)))
        
        summary["기본_지표"] = {
            "전체_이탈률": f"{churn_rate:.1f}%",
            "활성_사용자": active_users,
            "재활성_사용자": reactivated_users,
            "장기_미접속": long_term_inactive,
            "분석_기간": f"{analysis_data.get('start_month', 'N/A')} ~ {analysis_data.get('end_month', 'N/A')}"
        }
        
        # 선택된 세그먼트 정보 추가
        config = analysis_data.get('config', {})
        selected_segments = config.get('segments', {})
        summary["선택된_세그먼트"] = {
            "성별_분석": selected_segments.get('gender', False),
            "연령대_분석": selected_segments.get('age_band', False),
            "채널_분석": selected_segments.get('channel', False)
        }
        
        # 세그먼트 분석 요약 (선택된 세그먼트만)
        segments = analysis_data.get('segments', {})
        segment_names = {
            'gender': '성별',
            'age_band': '연령대', 
            'channel': '채널'
        }
        
        for segment_type, segment_data in segments.items():
            if segment_data and selected_segments.get(segment_type, False):
                segment_summary = []
                for item in segment_data:
                    item_churn_rate = self._convert_decimal(item.get('churn_rate', 0))
                    item_active = int(self._convert_decimal(item.get('current_active', 0)))
                    segment_summary.append({
                        "그룹": item.get('segment_value', 'Unknown'),
                        "이탈률": f"{item_churn_rate:.1f}%",
                        "활성사용자": item_active,
                        "신뢰도": "Uncertain" if item.get('is_uncertain', False) else "확실"
                    })
                summary["세그먼트_분석"][segment_names.get(segment_type, segment_type)] = segment_summary
        
        # 트렌드 분석 요약
        trends = analysis_data.get('trends', {})
        if trends:
            trend_data = trends.get('monthly_churn_rates', [])
            if len(trend_data) >= 2:
                first_rate = self._convert_decimal(trend_data[0].get('churn_rate', 0))
                last_rate = self._convert_decimal(trend_data[-1].get('churn_rate', 0))
                change = last_rate - first_rate
                
                summary["트렌드_분석"] = {
                    "기간": f"{len(trend_data)}개월",
                    "시작_이탈률": f"{first_rate:.1f}%",
                    "최종_이탈률": f"{last_rate:.1f}%",
                    "변화량": f"{change:+.1f}%p",
                    "트렌드": "상승" if change > 1 else "하락" if change < -1 else "안정"
                }
        
        # 데이터 품질 요약
        quality = analysis_data.get('data_quality', {})
        total_events = int(self._convert_decimal(quality.get('total_events', 0)))
        valid_events = int(self._convert_decimal(quality.get('valid_events', 0)))
        completeness = self._convert_decimal(quality.get('data_completeness', 0))
        unknown_ratio = self._convert_decimal(quality.get('unknown_ratio', 0))
        
        summary["데이터_품질"] = {
            "총_이벤트": total_events,
            "유효_이벤트": valid_events,
            "완전성": f"{completeness:.1f}%",
            "알수없음_비율": f"{unknown_ratio:.1f}%"
        }
        
        return summary
    
    def _create_analysis_prompt(self, data_summary: Dict) -> str:
        """LLM 분석을 위한 프롬프트 생성"""
        
        # 선택된 세그먼트 정보 확인
        selected_segments = data_summary.get('선택된_세그먼트', {})
        segment_analysis_available = any(selected_segments.values())
        
        prompt = f"""다음 이탈 분석 데이터를 바탕으로 주요 인사이트 3개와 권장 액션 3개를 생성해주세요.

## 분석 설정

### 선택된 세그먼트
{json.dumps(data_summary['선택된_세그먼트'], ensure_ascii=False, indent=2)}

## 분석 데이터

### 기본 지표
{json.dumps(data_summary['기본_지표'], ensure_ascii=False, indent=2)}"""

        # 세그먼트 분석이 있는 경우만 포함
        if segment_analysis_available and data_summary['세그먼트_분석']:
            prompt += f"""

### 세그먼트별 분석 (선택된 세그먼트만)
{json.dumps(data_summary['세그먼트_분석'], ensure_ascii=False, indent=2)}"""
        else:
            prompt += """

### 세그먼트별 분석
세그먼트 분석이 선택되지 않았습니다. 전체 사용자 기준으로만 분석하세요."""

        prompt += f"""

### 트렌드 분석
{json.dumps(data_summary['트렌드_분석'], ensure_ascii=False, indent=2)}

### 데이터 품질
{json.dumps(data_summary['데이터_품질'], ensure_ascii=False, indent=2)}

## 요청사항

1. **주요 인사이트 3개**: 데이터에서 발견된 가장 중요한 패턴이나 문제점을 존댓말로 설명해주세요
2. **권장 액션 3개**: 이탈률 개선을 위한 구체적이고 실행 가능한 방안을 존댓말로 제시해주세요

주의사항:
- 반드시 존댓말을 사용하여 응답해주세요
- 선택되지 않은 세그먼트(성별/연령대/채널)에 대해서는 언급하지 마세요
- 선택된 세그먼트만 분석하고 인사이트를 제공하세요
- 통계적으로 유의미한 차이(5%p 이상)만 언급해주세요
- 데이터가 부족한 세그먼트는 "Uncertain" 표기해주세요
- 구체적인 수치와 함께 설명해주세요
- 실무진이 바로 실행할 수 있는 액션을 제시해주세요

금지사항:
- 데이터에 없는 정보를 추측하거나 가정하지 마세요
- 개인정보나 민감한 정보를 언급하지 마세요
- 차별적이거나 편향된 분석을 제공하지 마세요
- 법적 조언이나 의료적 조언을 제공하지 마세요
- 과장되거나 부정확한 표현을 사용하지 마세요
- 선택되지 않은 세그먼트의 데이터를 임의로 해석하지 마세요
- 통계적으로 유의미하지 않은 차이를 과장하여 설명하지 마세요
- 불확실한 데이터를 확실한 것처럼 표현하지 마세요"""

        return prompt
    
    def _filter_and_validate_responses(self, responses: List[str], response_type: str) -> List[str]:
        """응답 필터링 및 검증"""
        if not responses:
            return []
        
        filtered_responses = []
        prohibited_terms = [
            '개인정보', '민감정보', '법적', '의료', '차별', '편향', 
            '추측', '가정', '확실하지', '불확실', '과장'
        ]
        
        for response in responses:
            if not isinstance(response, str) or len(response.strip()) == 0:
                continue
                
            # 금지된 용어가 포함된 응답 필터링
            if any(term in response for term in prohibited_terms):
                logger.warning(f"금지된 용어가 포함된 {response_type} 응답 필터링: {response[:50]}...")
                continue
            
            # 응답 길이 검증 (너무 짧거나 긴 응답 제외)
            if len(response) < 10 or len(response) > 500:
                logger.warning(f"부적절한 길이의 {response_type} 응답 필터링: {len(response)}자")
                continue
            
            # 기본적인 품질 검증 통과
            filtered_responses.append(response.strip())
        
        # 최대 개수 제한
        return filtered_responses[:3]
    
    def _generate_fallback_insights(self, analysis_data: Dict) -> Dict[str, List[str]]:
        """LLM 사용 불가 시 실제 데이터 기반 기본 분석 제공"""
        
        # 실제 데이터를 기반으로 한 기본 인사이트 생성
        insights = []
        actions = []
        
        try:
            # 메트릭 데이터 추출
            metrics = analysis_data.get('metrics', {})
            segments = analysis_data.get('segments', {})
            trends = analysis_data.get('trends', {})
            data_quality = analysis_data.get('data_quality', {})
            
            # 1. 전체 이탈률 인사이트
            churn_rate = metrics.get('churn_rate', 0)
            active_users = metrics.get('active_users', 0)
            
            if churn_rate > 25:
                insights.append(f"⚠️ 전체 이탈률이 {churn_rate:.1f}%로 매우 높은 수준입니다. 즉시 대응이 필요합니다.")
                actions.append("🚨 긴급 이탈 방지 프로그램 도입 및 사용자 피드백 수집")
            elif churn_rate > 15:
                insights.append(f"📊 전체 이탈률이 {churn_rate:.1f}%로 주의가 필요한 수준입니다.")
                actions.append("📋 이탈 위험 사용자 식별 및 맞춤형 리텐션 캠페인 실행")
            elif churn_rate > 5:
                insights.append(f"✅ 전체 이탈률이 {churn_rate:.1f}%로 양호한 수준입니다.")
                actions.append("✨ 현재 서비스 품질 유지 및 사용자 만족도 지속 모니터링")
            else:
                insights.append(f"🎉 전체 이탈률이 {churn_rate:.1f}%로 매우 우수한 수준입니다.")
                actions.append("🏆 우수한 리텐션 전략을 다른 세그먼트에도 확대 적용")
            
            # 2. 활성 사용자 트렌드 인사이트
            previous_users = metrics.get('previous_active_users', 0)
            if previous_users > 0:
                growth = ((active_users - previous_users) / previous_users * 100)
                if growth > 10:
                    insights.append(f"📈 활성 사용자가 {active_users:,}명으로 {growth:.1f}% 급성장했습니다.")
                    actions.append("🚀 성장 동력을 분석하여 성공 요인을 다른 영역에 적용")
                elif growth > 0:
                    insights.append(f"📊 활성 사용자가 {active_users:,}명으로 {growth:.1f}% 증가했습니다.")
                    actions.append("📈 성장세 유지를 위한 사용자 경험 개선 지속")
                elif growth > -10:
                    insights.append(f"📉 활성 사용자가 {active_users:,}명으로 {abs(growth):.1f}% 감소했습니다.")
                    actions.append("🔍 사용자 감소 원인 분석 및 개선 방안 수립")
                else:
                    insights.append(f"⚠️ 활성 사용자가 {active_users:,}명으로 {abs(growth):.1f}% 급감했습니다.")
                    actions.append("🚨 긴급 사용자 복귀 캠페인 및 서비스 개선 필요")
            
            # 3. 세그먼트 기반 인사이트 (가장 높은 이탈률 세그먼트)
            highest_churn_segment = None
            highest_churn_rate = 0
            segment_type_name = ""
            
            for seg_type, seg_data in segments.items():
                if seg_data and isinstance(seg_data, list) and len(seg_data) > 0:
                    for segment in seg_data:
                        if segment.get('churn_rate', 0) > highest_churn_rate:
                            highest_churn_rate = segment.get('churn_rate', 0)
                            highest_churn_segment = segment
                            segment_type_name = seg_type
            
            if highest_churn_segment and highest_churn_rate > 15:
                segment_names = {
                    'gender': {'M': '남성', 'F': '여성'},
                    'age_band': {'10s': '10대', '20s': '20대', '30s': '30대', '40s': '40대', '50s': '50대', '60s': '60대'},
                    'channel': {'web': '웹', 'app': '모바일 앱'}
                }
                
                segment_display = segment_names.get(segment_type_name, {}).get(
                    highest_churn_segment['segment_value'], 
                    highest_churn_segment['segment_value']
                )
                
                uncertain_note = " (모수 부족)" if highest_churn_segment.get('is_uncertain', False) else ""
                insights.append(f"🎯 {segment_display} 세그먼트에서 높은 이탈률({highest_churn_rate:.1f}%)을 보입니다{uncertain_note}.")
                
                # 세그먼트별 맞춤 액션
                if segment_type_name == 'gender':
                    if highest_churn_segment['segment_value'] == 'F':
                        actions.append("👥 여성 사용자 대상 맞춤형 콘텐츠 및 커뮤니티 활동 강화")
                    else:
                        actions.append("👥 남성 사용자 대상 맞춤형 서비스 및 기능 개선")
                elif segment_type_name == 'age_band':
                    if highest_churn_segment['segment_value'] in ['50s', '60s']:
                        actions.append("👴 50대 이상 사용자를 위한 사용성 개선 및 신규 가이드 제공")
                    elif highest_churn_segment['segment_value'] in ['10s', '20s']:
                        actions.append("👶 젊은 사용자층을 위한 트렌디한 콘텐츠 및 소셜 기능 강화")
                    else:
                        actions.append(f"🎯 {segment_display} 연령대를 위한 전용 서비스 및 UI/UX 개선")
                elif segment_type_name == 'channel':
                    if highest_churn_segment['segment_value'] == 'app':
                        actions.append("📱 모바일 앱 사용자 경험 개선 및 푸시 알림 최적화")
                    else:
                        actions.append("💻 웹 플랫폼 사용자 경험 개선 및 기능 최적화")
            
            # 4. 장기 미접속 사용자 인사이트
            long_term_inactive = metrics.get('long_term_inactive', 0)
            if long_term_inactive > 0 and active_users > 0:
                inactive_ratio = (long_term_inactive / (active_users + long_term_inactive)) * 100
                if inactive_ratio > 15:
                    insights.append(f"⏳ 장기 미접속 사용자가 전체의 {inactive_ratio:.1f}%로 높은 수준입니다.")
                    actions.append("🔄 장기 미접속자 대상 복귀 유도 캠페인 및 개인화된 알림 시스템 구축")
            
            # 5. 데이터 품질 기반 인사이트
            if data_quality:
                completeness = data_quality.get('data_completeness', 100)
                if completeness < 90:
                    insights.append(f"📊 데이터 완전성이 {completeness:.1f}%로 개선이 필요합니다.")
                    actions.append("🔧 데이터 수집 프로세스 개선 및 품질 관리 강화")
            
            # 인사이트가 부족한 경우 기본 메시지 추가
            if len(insights) == 0:
                insights.append("📊 현재 데이터를 기반으로 한 기본 분석이 완료되었습니다.")
                
            if len(actions) == 0:
                actions.append("📈 지속적인 사용자 행동 모니터링 및 데이터 기반 의사결정 수행")
            
            # 최대 3개까지만 반환
            insights = insights[:3]
            actions = actions[:3]
            
            # AI 분석 안내 메시지 추가 (마지막에)
            if len(insights) < 3:
                insights.append("🤖 OpenAI API 키 설정 시 더 정확하고 상세한 AI 분석을 제공받을 수 있습니다.")
            if len(actions) < 3:
                actions.append("⚙️ AI 기반 권장 액션 활성화를 위해 OpenAI API 키를 설정하세요.")
            
        except Exception as e:
            logger.error(f"기본 분석 생성 중 오류: {e}")
            # 오류 발생 시 최소한의 메시지
            insights = [
                "📊 데이터 분석을 완료했습니다.",
                "🔍 더 상세한 분석을 위해 데이터를 검토해주세요.",
                "🤖 AI 기반 인사이트를 위해 OpenAI API 키 설정을 권장합니다."
            ]
            actions = [
                "📈 정기적인 이탈률 모니터링 및 트렌드 분석 수행",
                "👥 주요 사용자 세그먼트별 맞춤형 전략 수립",
                "🔑 OpenAI API 키 설정으로 AI 기반 분석 활성화"
            ]
        
        return {
            'insights': insights,
            'actions': actions,
            'generated_by': 'basic_analysis',
            'timestamp': datetime.now().isoformat(),
            'setup_required': False,
            'data_driven': True
        }

# 전역 인스턴스
llm_generator = LLMInsightGenerator()
