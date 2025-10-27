C:\Users\201\Downloads\ethics_data 에 있는 소스 분석해서 현재 프로젝트에서 구동할 수 있도록 구현해줘
- 필요한 소스만 옮겨줘
- 새로 구현하는 모든 파일명 앞에는 "ethics_" 붙여줘
- 필요한 패키지는 requirements.txt에 추가해줘
- .env 파일은 최상단에 있어. OPENAI_API_KEY, OPENAI_MODEL, DB_HOST, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
- 다음 구조 참고해줘
app/
├── main.py                 # FastAPI 엔트리포인트
├── settings.py             # 환경 설정
├── ethics/                 # *추가되는 소스는 여기에 모아줘
├── api/
│   ├── routes_public.py    # 페이지 라우팅
│   └── routes_health.py    # 헬스체크
├── templates/
│   ├── base.html           # 기본 레이아웃
│   ├── components/         # 재사용 컴포넌트
│   │   ├── nav.html
│   │   ├── footer.html
│   │   └── alert.html
│   └── pages/              # 페이지 템플릿
│       ├── home.html
│       ├── api_console.html
│       ├── bounce.html
│       ├── trends.html
│       ├── reports.html
│       ├── ethics_analyze.html
│       └── ethics_dashboard.html
└── static/
    ├── css/
    │   └── app.css         # 스타일시트
    ├── js/
    │   └── app.js          # JavaScript 로직
    └── img/                # 이미지 리소스

#대응되는 페이지 
C:\Users\201\Downloads\ethics_data\static\index.html -> app\templates\pages\ethics_dashboard.html
C:\Users\201\Downloads\ethics_data\static\analyze.html -> app\templates\pages\ethics_analyze.html

