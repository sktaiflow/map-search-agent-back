# map-search-agent
map-search-agent repository in "데이터 모델링팀"

## 환경 설정 가이드

### Neo4j 연결 설정
Neo4j 연결 URL은 실행 환경에 따라 다르게 설정해야 합니다:
- LangGraph 환경: `url="bolt://localhost:7687"`
- OpenWebUI 환경: `url="bolt://neo4j-gds-apoc-n10s:7687"`

### Local 개발 환경 설정

1. **LangGraph 서버 실행**
   ```bash
   langgraph serve
   ```

2. **Neo4j 컨테이너 실행**
   ```bash
   docker compose up -d
   ```

### 주의사항
- LangGraph 환경에서는 Neo4j 연결 URL을 `bolt://localhost:7687`로 설정합니다.
- OpenWebUI 환경에서는 `bolt://neo4j-gds-apoc-n10s:7687`를 사용합니다.
- Neo4j 기본 접속 정보:
  - Username: neo4j
  - Password: neo4jpassword
  - Port: 7687

## 시스템 아키텍처 다이어그램

```mermaid
stateDiagram-v2
    direction LR  
        [user_query] --> Preprocessing_Layer
        Preprocessing_Layer --> OntolgyLayer

    state Preprocessing_Layer {
        [*] --> Entity/Relation_Extraction
        Entity/Relation_Extraction: 개채명/관계 추출
    }

    state OntolgyLayer {
        [*] --> termModification 
            termModification--> termExpansion
            termExpansion--> queryExpansion
            queryExpansion--> [*]

        termModification --> knowledgeExtraction 
        knowledgeExtraction--> [*]
    }
    OntolgyLayer --> AgentProcessor
    AgentProcessor --> Generate/Refined
    Generate/Refined: 답변 생성 및 체크 

    state AgentProcessor {
        KnowledgeAndQuery: 추출된 지식
        Query: 변환된 쿼리
        [*] --> KnowledgeAndQuery
        [*] --> Query
        KnowledgeAndQuery --> Plan
        Query --> Plan
        Plan --> Action
        Action --> Tools: Tool selection
        Tools --> Action: Return Tool
        state Tools {            
            Tool1: 사용자 정보 조회  
            Tool2: 상품 메타 검색 
            Tool3: 기타  
            
            state Tool1 {
                user: 사용자 기본 정보 조회
                product: 사용자 가입 상품 조회 
            }
            
            state Tool2 {
                direction LR
                graph_search: 그래프 검색
                es: ES 검색
                vector: Vector 검색
                graph_traverse: 그래프 탐색
            }
        }
        Action --> Validator
        Validator --> Replan
        Replan --> Action: 필요시 
        Replan --> END

        Plan: 계획 수립
        Validator: Action Validator

    }

```