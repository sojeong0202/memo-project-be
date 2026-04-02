# memo-project 백엔드 구현 계획서

## 프로젝트 구조

```
memo-project-be/
├── app/
│   ├── main.py                  # FastAPI 앱 진입점
│   ├── core/
│   │   ├── config.py            # 환경변수 설정 (pydantic-settings)
│   │   ├── database.py          # SQLAlchemy Async 엔진 및 세션
│   │   └── security.py          # JWT 토큰 생성/검증
│   ├── models/
│   │   ├── user.py              # Users ORM 모델
│   │   ├── node.py              # Nodes ORM 모델 (pgvector 포함)
│   │   └── edge.py              # Edges ORM 모델
│   ├── schemas/
│   │   ├── auth.py              # 인증 관련 Pydantic 스키마
│   │   ├── node.py              # 노드 요청/응답 스키마
│   │   ├── edge.py              # 엣지 요청/응답 스키마
│   │   └── graph.py             # 그래프 조회 응답 스키마
│   ├── routers/
│   │   ├── auth.py              # /api/auth 라우터
│   │   ├── nodes.py             # /api/nodes 라우터
│   │   ├── edges.py             # /api/edges 라우터
│   │   └── graph.py             # /api/graph 라우터
│   ├── services/
│   │   ├── auth_service.py      # Google OAuth 검증 로직
│   │   ├── ai_service.py        # OpenAI 요약 + 임베딩 생성 + 색상 해싱
│   │   └── graph_service.py     # 유사도 계산 + 엣지 생성 로직
│   └── dependencies.py          # 공통 의존성 (현재 유저 추출 등)
├── migrations/                  # Alembic 마이그레이션
├── tests/
├── docker-compose.yml           # PostgreSQL + pgvector 컨테이너
├── .env
├── .env.example
├── requirements.txt
└── alembic.ini
```

---

## DB 설계

### Users 테이블
| 컬럼 | 타입 | 설명 |
|---|---|---|
| `user_id` | UUID (PK) | 내부 식별자 |
| `google_id` | VARCHAR UNIQUE NOT NULL | 구글 OAuth sub |
| `email` | VARCHAR UNIQUE NOT NULL | 이메일 |
| `created_at` | TIMESTAMPTZ DEFAULT now() | 가입일 |

### Nodes 테이블
| 컬럼 | 타입 | 설명 |
|---|---|---|
| `node_id` | UUID (PK) | 노드 식별자 |
| `user_id` | UUID (FK → Users) | 소유 유저 |
| `original_text` | TEXT NOT NULL | 입력 원문 |
| `summary` | TEXT | AI 요약 |
| `keywords` | VARCHAR[] | 핵심 키워드 1~2개 (예: ["AI", "머신러닝"]) |
| `embedding` | VECTOR(1536) | text-embedding-3-small 기본 출력 차원 |
| `brightness` | SMALLINT DEFAULT 1 | 업데이트 횟수 반영 밝기 (1~10) |
| `category_color` | VARCHAR(7) | 첫 번째 키워드 해시 기반 HEX 색상 (예: #A3B4C5) |
| `created_at` | TIMESTAMPTZ DEFAULT now() | 생성일 |
| `updated_at` | TIMESTAMPTZ DEFAULT now() | 마지막 업데이트 |

**인덱스:**
- `embedding` 컬럼에 `HNSW` 인덱스 (`vector_cosine_ops`)
  - 2025 기준 pgvector 공식 권장 기본값
  - 데이터 없이도 인덱스 생성 가능 (IVFFlat은 학습 데이터 필요)
  - 파라미터: `m = 16, ef_construction = 200` (기본값으로 시작)
  - IVFFlat은 5000만 건 이상의 정적 대용량 데이터에서만 유리
- `user_id` B-tree 인덱스 — 유저별 노드 필터링

### Edges 테이블
| 컬럼 | 타입 | 설명 |
|---|---|---|
| `edge_id` | UUID (PK) | 엣지 식별자 |
| `source_node_id` | UUID (FK → Nodes, ON DELETE CASCADE) | 출발 노드 |
| `target_node_id` | UUID (FK → Nodes, ON DELETE CASCADE) | 도착 노드 |
| `similarity_score` | FLOAT NOT NULL | 코사인 유사도 값 |
| `is_manual` | BOOLEAN DEFAULT false | 수동 생성 여부 |
| `created_at` | TIMESTAMPTZ DEFAULT now() | 연결 생성일 |

**제약:**
- `(source_node_id, target_node_id)` UNIQUE — 중복 엣지 방지
- 노드 삭제 시 연결 엣지 CASCADE DELETE (구조 재계산 없음)

---

## AI 처리 파이프라인 (노드 생성 흐름)

```
POST /api/nodes { "text": "..." }
│
├── 1. [ai_service] OpenAI Chat API — 요약 + 키워드 추출
│      모델: gpt-4o-mini
│      출력: { "summary": "...", "keywords": ["키워드1", "키워드2"] }
│
├── 2. [ai_service] 색상 해싱
│      keywords[0]을 해시하여 HEX 색상 자동 부여
│      동일 키워드 → 항상 동일 색상 (시각적 일관성)
│
├── 3. [ai_service] OpenAI Embeddings API — 원문 벡터화
│      모델: text-embedding-3-small (차원: 1536)
│
├── 4. [graph_service] pgvector 유사도 검색
│      현재 유저의 기존 노드들과 코사인 유사도 계산
│      쿼리: ORDER BY embedding <=> :new_vector LIMIT 20
│
├── 5. [graph_service] 분기 처리
│      similarity >= DUPLICATE_THRESHOLD (기본 0.95)
│        → 기존 노드 updated_at 갱신, brightness +1 (최대 10)
│        → 새 노드 생성하지 않음
│      EDGE_THRESHOLD (기본 0.8) <= similarity < 0.95
│        → 새 Edge 레코드 생성
│      similarity < EDGE_THRESHOLD
│        → 독립 노드로 저장
│
│      * EDGE_THRESHOLD, DUPLICATE_THRESHOLD는 .env에서 조정 가능
│
└── 6. 응답: 생성된 노드 + 새로 연결된 엣지 목록 반환
```

---

## API 엔드포인트 명세

### Auth — `/api/auth`
| Method | Endpoint | 기능 | Request Body | Response |
|---|---|---|---|---|
| POST | `/api/auth/google` | Google id_token 검증 및 JWT(Bearer) 발급 | `{ "token": "id_token" }` | `{ "access_token", "token_type": "bearer", "user_id" }` |
| GET | `/api/auth/me` | 현재 로그인 유저 정보 조회 | Header: `Authorization: Bearer <JWT>` | `{ user 객체 }` |

### Nodes — `/api/nodes`
| Method | Endpoint | 기능 | Request | Response |
|---|---|---|---|---|
| POST | `/api/nodes` | 메모 생성 + AI 파이프라인 + 엣지 자동 연결 | `{ "text": "..." }` | `{ "node": {...}, "new_edges": [...] }` |
| GET | `/api/nodes/{id}` | 단일 노드 상세 조회 | Path param | `{ node 상세 }` |
| PATCH | `/api/nodes/{id}` | 노드 요약/키워드 수동 수정 (일부 필드만 업데이트) | `{ "summary": "...", "keywords": [...] }` | `{ updated node }` |
| DELETE | `/api/nodes/{id}` | 노드 삭제 (연결 엣지 CASCADE) | Path param | `{ "status": "success" }` |

### Edges — `/api/edges`
| Method | Endpoint | 기능 | Request | Response |
|---|---|---|---|---|
| DELETE | `/api/edges/{id}` | 엣지 수동 삭제 | Path param | `{ "status": "success" }` |

### Graph — `/api/graph`
| Method | Endpoint | 기능 | Request | Response |
|---|---|---|---|---|
| GET | `/api/graph` | 전체 지식 그래프 데이터 조회 | Header: Bearer JWT | `{ "nodes": [...], "edges": [...] }` |

---

## 환경변수 (.env)

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/memodb
OPENAI_API_KEY=sk-...
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

EDGE_THRESHOLD=0.8
DUPLICATE_THRESHOLD=0.95
```

---

## 구현 단계별 체크리스트

### Phase 1 — 프로젝트 초기 세팅 + Docker ✅
- [x] `docker-compose.yml` 작성 — `ankane/pgvector` 이미지로 PostgreSQL + pgvector 컨테이너 구성
- [x] 가상환경 생성 및 `requirements.txt` 작성
  - FastAPI, uvicorn, SQLAlchemy[asyncio], `asyncpg<0.29.0` (0.29.0+는 create_async_engine 호환 이슈), pgvector, alembic
  - pydantic-settings, python-jose[cryptography], httpx, openai, google-auth
- [x] `app/core/config.py` — pydantic-settings 기반 환경변수 로더 (임계값 포함)
- [x] `app/core/database.py` — AsyncEngine + AsyncSession 팩토리
- [x] `app/main.py` — FastAPI 앱 생성, CORS, 라우터 등록
- PR: sojeong0202/memo-project-be#8

### Phase 2 — DB 모델 및 마이그레이션 ✅
- [x] `app/models/user.py` — Users ORM 모델
- [x] `app/models/node.py` — Nodes ORM 모델 (pgvector Column 포함)
- [x] `app/models/edge.py` — Edges ORM 모델 (CASCADE 설정 포함)
- [x] Alembic 초기화 및 `env.py` async 설정
- [x] 초기 마이그레이션 파일 생성 및 적용 (HNSW 인덱스 포함)
- PR: sojeong0202/memo-project-be#9

### Phase 3 — 인증 (Auth) ✅
- [x] `app/services/auth_service.py` — Google id_token 검증 (google-auth `verify_oauth2_token`, 공개키 캐싱 적용으로 레이턴시 감소)
- [x] `app/core/security.py` — JWT 발급/검증 유틸 (Bearer Token)
- [x] `app/schemas/auth.py` — 요청/응답 스키마
- [x] `app/routers/auth.py` — POST `/api/auth/google`, GET `/api/auth/me`
- [x] `app/dependencies.py` — `get_current_user` 의존성 함수
- PR: sojeong0202/memo-project-be#10

### Phase 4 — AI 서비스 ✅
- [x] `app/services/ai_service.py` — OpenAI Chat API 요약/키워드 추출
  - 모델: `gpt-4o-mini`
  - `response_format={"type": "json_schema", "json_schema": {...}}` (Structured Outputs) 사용
  - JSON mode와 달리 스키마 구조를 강제 보장 → 파싱 실패 없음
- [x] `app/services/ai_service.py` — 키워드 해시 기반 HEX 색상 자동 부여 로직
- [x] `app/services/ai_service.py` — OpenAI Embeddings API 벡터화 (text-embedding-3-small, 1536차원)
- PR: sojeong0202/memo-project-be#11

### Phase 5 — 노드 및 그래프 서비스 ✅
- [x] `app/services/graph_service.py` — pgvector 코사인 유사도 검색 쿼리 (HNSW)
- [x] `app/services/graph_service.py` — 엣지 자동 생성 로직 (EDGE_THRESHOLD)
- [x] `app/services/graph_service.py` — 중복 노드 업데이트 로직 (DUPLICATE_THRESHOLD, brightness +1)
- PR: sojeong0202/memo-project-be#12

### Phase 6 — API 라우터 ✅
- [x] `app/schemas/` — 모든 Pydantic 요청/응답 스키마
- [x] `app/routers/nodes.py` — CRUD + AI 파이프라인 통합
- [x] `app/routers/edges.py` — DELETE 엣지
- [x] `app/routers/graph.py` — GET 전체 그래프
- PR: sojeong0202/memo-project-be#13

### Phase 7 — 테스트 및 마무리
- [ ] 각 엔드포인트 통합 테스트 (pytest + httpx AsyncClient)
- [ ] `README.md` — Docker 기반 로컬 실행 가이드

---

## 주요 기술 결정 사항 요약

| 항목 | 결정 | 이유 |
|---|---|---|
| 요약 모델 | `gpt-4o-mini` | 저비용, JSON 구조화 출력 지원 |
| 임베딩 모델 | `text-embedding-3-small` | 기본 1536차원, 비용 대비 성능 최적 |
| pgvector 인덱스 | `HNSW` (m=16, ef_construction=200) | 2025 pgvector 공식 권장값, 빈 테이블에서도 생성 가능, 소규모~중규모 모두 적합 |
| 엣지 임계값 | `EDGE_THRESHOLD=0.4` (env로 조정 가능) | text-embedding-3-small 한국어 단문 기준 실측값, AI관련 주제 0.4~0.53 범위 |
| 중복 임계값 | `DUPLICATE_THRESHOLD=0.95` (env로 조정 가능) | 거의 동일 내용 처리 기준 |
| JWT 방식 | Bearer Token (Authorization 헤더) | 프론트 협의 완료 |
| 색상 분류 | 첫 번째 키워드 해시 → HEX 자동 부여 | 시각화 일관성, Phase 4에 구현 |
| DB 로컬 환경 | Docker Compose (`ankane/pgvector`) | pgvector 로컬 설치 복잡도 회피 |
