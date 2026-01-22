from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.config import settings
import logging
import json

logger = logging.getLogger(__name__)


class QueryPlanner:
    """Analyze and plan queries for optimal retrieval."""
    
    def __init__(self):
        """Initialize the query planner with LLM."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.3
        )
    
    def analyze_query(self, query: str, current_stage: str = "welcome") -> Dict[str, Any]:
        """
        Analyze a user query to determine retrieval strategy.
        
        Args:
            query: User's question
            current_stage: Current onboarding stage
            
        Returns:
            Dictionary with query analysis
        """
        system_prompt = """You are a query analyzer for an onboarding assistant.
Analyze the user's query and determine:
1. The intent (question, request_help, navigation, feedback, etc.)
2. Whether document retrieval is needed
3. Relevant categories (introduction, setup, projects, features, integrations, security, pricing, support, mobile, productivity)
4. The onboarding stage relevance

Respond in JSON format:
{
    "intent": "question|request_help|navigation|feedback|greeting",
    "needs_retrieval": true|false,
    "categories": ["category1", "category2"],
    "complexity": "simple|moderate|complex",
    "suggested_k": 3-8
}"""
        
        user_prompt = f"""Query: {query}
Current Stage: {current_stage}

Analyze this query."""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            analysis = json.loads(content)
            
            logger.info(f"Query analysis: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            return {
                "intent": "question",
                "needs_retrieval": True,
                "categories": [],
                "complexity": "moderate",
                "suggested_k": 5
            }
    
    def generate_search_queries(self, original_query: str, analysis: Dict[str, Any]) -> List[str]:
        """
        Generate multiple search queries for better retrieval.
        
        Args:
            original_query: Original user query
            analysis: Query analysis from analyze_query
            
        Returns:
            List of search queries
        """
        if analysis.get("complexity") == "simple":
            return [original_query]
        
        system_prompt = """Generate 2-3 alternative phrasings of the user's query to improve document retrieval.
Make queries more specific and focused on key concepts.
Return as JSON array: ["query1", "query2", "query3"]"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Original query: {original_query}")
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            queries = json.loads(content)
            
            all_queries = [original_query] + queries
            logger.info(f"Generated {len(all_queries)} search queries")
            return all_queries
            
        except Exception as e:
            logger.error(f"Error generating search queries: {e}")
            return [original_query]
