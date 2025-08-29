"""
Cypher API 테스트 코드
이 파일은 Cypher API의 기능을 테스트하기 위한 간단한 스크립트입니다.
FastAPI 애플리케이션이 실행 중일 때 이 스크립트를 실행하여 API를 테스트할 수 있습니다.
"""
import asyncio
import aiohttp
import json


async def test_cypher_api():
    """Cypher API 테스트 함수"""
    base_url = "http://localhost:8000"  # 서버 URL (실제 환경에 맞게 수정)
    
    async with aiohttp.ClientSession() as session:
        
        print("=== Cypher API 테스트 시작 ===\n")
        
        # 간단한 Cypher 쿼리 테스트
        print("간단한 Cypher 쿼리 테스트")
        simple_query = {
            "query": "RETURN 'Hello, Neo4j!' as greeting, 42 as answer"
        }
        
        try:
            async with session.post(
                f"{base_url}/v1/cypher/execute",
                json=simple_query,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                print(f"Status: {response.status}")
                print(f"Query: {simple_query['query']}")
                print(f"Response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"쿼리 실행 실패: {e}")
        
        print("\n" + "="*50 + "\n")
        
        # 3. 파라미터를 사용한 쿼리 테스트
        print("3. 파라미터를 사용한 쿼리 테스트")
        param_query = {
            "query": "RETURN $name as name, $age as age",
            "parameters": {
                "name": "Alice",
                "age": 30
            }
        }
        
        try:
            async with session.post(
                f"{base_url}/v1/cypher/execute",
                json=param_query,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                print(f"Status: {response.status}")
                print(f"Query: {param_query['query']}")
                print(f"Parameters: {param_query['parameters']}")
                print(f"Response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"파라미터 쿼리 실행 실패: {e}")
        
        print("\n" + "="*50 + "\n")
        
        # 4. 잘못된 쿼리 테스트 (에러 처리 확인)
        print("4. 잘못된 쿼리 테스트 (에러 처리 확인)")
        invalid_query = {
            "query": "INVALID CYPHER QUERY"
        }
        
        try:
            async with session.post(
                f"{base_url}/v1/cypher/execute",
                json=invalid_query,
                headers={"Content-Type": "application/json"}
            ) as response:
                result = await response.json()
                print(f"Status: {response.status}")
                print(f"Query: {invalid_query['query']}")
                print(f"Response: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"잘못된 쿼리 테스트 실패: {e}")
        
        print("\n=== Cypher API 테스트 완료 ===")


if __name__ == "__main__":
    """
    테스트 스크립트 실행
    
    사용 방법:
    1. FastAPI 서버를 먼저 실행하세요: uvicorn app.server:app --reload
    2. 이 스크립트를 실행하세요: python test_cypher_api.py
    """
    print("Cypher API 테스트를 시작합니다...")
    print("주의: FastAPI 서버가 http://localhost:8000 에서 실행 중이어야 합니다.")
    print()
    
    asyncio.run(test_cypher_api())
