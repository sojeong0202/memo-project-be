# memo-project-be

텍스트 메모를 AI가 자동 요약·임베딩하고, 의미 기반으로 연결하여 지식 그래프로 시각화하는 서비스의 백엔드 API입니다.

## 기술 스택

- **Framework:** FastAPI (Python 3.12)
- **Database:** PostgreSQL + pgvector (HNSW 인덱스)
- **ORM:** SQLAlchemy 2.0 (Async)
- **AI:** OpenAI `gpt-4o-mini` (요약), `text-embedding-3-small` (임베딩)
- **Auth:** Google OAuth 2.0 + JWT Bearer Token

## 로컬 실행 가이드

### 1. 사전 준비

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치 및 실행
- Python 3.12 설치
- Google Cloud Console에서 OAuth 2.0 클라이언트 ID 발급
- OpenAI API 키 발급

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일 생성:

```
DATABASE_URL=postgresql+asyncpg://memo_user:memo_password@localhost:5432/memodb
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080
EDGE_THRESHOLD=0.4
DUPLICATE_THRESHOLD=0.95
```

### 3. DB 실행

```bash
docker compose up -d
```

### 4. 가상환경 및 의존성 설치

```bash
python -m venv .venv

# Windows (Git Bash)
source .venv/Scripts/activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 5. DB 마이그레이션

```bash
alembic upgrade head
```

### 6. 서버 실행

```bash
uvicorn app.main:app --reload
```

서버 기동 후 접속:
- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

## 테스트 실행

```bash
pytest tests/ -v
```

## API 목록

| Method | Endpoint | 인증 | 설명 |
|---|---|---|---|
| POST | `/api/auth/google` | 불필요 | Google id_token 검증 → JWT 발급 |
| GET | `/api/auth/me` | 필요 | 현재 유저 정보 조회 |
| POST | `/api/nodes` | 필요 | 메모 생성 + AI 처리 + 엣지 자동 연결 |
| GET | `/api/nodes/{id}` | 필요 | 단일 노드 조회 |
| PATCH | `/api/nodes/{id}` | 필요 | 노드 요약/키워드 수정 |
| DELETE | `/api/nodes/{id}` | 필요 | 노드 삭제 |
| DELETE | `/api/edges/{id}` | 필요 | 엣지 수동 삭제 |
| GET | `/api/graph` | 필요 | 전체 지식 그래프 조회 |
