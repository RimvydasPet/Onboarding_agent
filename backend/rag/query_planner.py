from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class QueryPlanner:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1
        )
    
    def analyze_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        
        system_prompt = """You are a query analyzer for an onboarding assistant.
Analyze the user's query and determine:
1. Intent (question, request_help, navigate, feedback, other)
2. Topic (account, features, getting_started, troubleshooting, other)
3. Complexity (simple, moderate, complex)
4. Requires_retrieval (true/false) - whether we need to search documentation
5. Suggested_keywords - list of keywords to search for

Respond in JSON format only."""

        user_prompt = f"""Query: {query}

Context: {json.dumps(context, indent=2)}

Analyze this query and respond with JSON."""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            analysis = json.loads(content.strip())
            logger.info(f"Query analysis: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {
                "intent": "question",
                "topic": "other",
                "complexity": "moderate",
                "requires_retrieval": True,
                "suggested_keywords": [query]
            }
    
    def generate_search_queries(self, query: str, analysis: Dict[str, Any]) -> List[str]:
        queries = [query]
        
        if analysis.get("suggested_keywords"):
            for keyword in analysis["suggested_keywords"][:3]:
                if keyword.lower() not in query.lower():
                    queries.append(f"{query} {keyword}")
        
        if analysis.get("topic") and analysis["topic"] != "other":
            queries.append(f"{analysis['topic']}: {query}")
        
        return list(set(queries))[:3]
    
    def should_retrieve(self, query: str, analysis: Dict[str, Any]) -> bool:
        if not analysis.get("requires_retrieval", True):
            return False
        
        simple_greetings = ["hi", "hello", "hey", "thanks", "thank you", "bye"]
        if query.lower().strip() in simple_greetings:
            return False
        
        return True
    
    def plan_retrieval_strategy(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        complexity = analysis.get("complexity", "moderate")
        
        if complexity == "simple":
            strategy = {
                "method": "similarity",
                "k": 3,
                "rerank": False
            }
        elif complexity == "complex":
            strategy = {
                "method": "mmr",
                "k": 7,
                "fetch_k": 20,
                "rerank": True
            }
        else:
            strategy = {
                "method": "similarity",
                "k": 5,
                "rerank": True
            }
        
        return strategy
