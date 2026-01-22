from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.agent.state import OnboardingAgentState
from backend.rag.agentic_rag import AgenticRAG
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory
from backend.config import settings
from backend.database.connection import get_db
import logging

logger = logging.getLogger(__name__)


class AgentNodes:
    """Node functions for the LangGraph agent."""
    
    def __init__(self):
        """Initialize agent nodes with required components."""
        self.rag = AgenticRAG()
        self.short_term_memory = ShortTermMemory()
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7
        )
        logger.info("Initialized AgentNodes")
    
    def analyze_input(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """
        Analyze user input to determine if retrieval is needed.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with query analysis
        """
        logger.info("Node: analyze_input")
        
        try:
            analysis = self.rag.query_planner.analyze_query(
                state["user_input"],
                state["current_stage"]
            )
            
            state["query_analysis"] = analysis
            state["needs_retrieval"] = analysis.get("needs_retrieval", True)
            
            logger.info(f"Query analysis complete: needs_retrieval={state['needs_retrieval']}")
            
        except Exception as e:
            logger.error(f"Error in analyze_input: {e}")
            state["needs_retrieval"] = True
            state["error"] = str(e)
        
        return state
    
    def load_memory(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """
        Load relevant memories from short-term and long-term storage.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with loaded memories
        """
        logger.info("Node: load_memory")
        
        try:
            recent_messages = self.short_term_memory.get_messages(
                state["session_id"],
                limit=5
            )
            
            state["short_term_context"] = {
                "recent_messages": recent_messages,
                "message_count": len(recent_messages)
            }
            
            db = next(get_db())
            ltm = LongTermMemory(db)
            
            important_memories = ltm.get_important_memories(
                state["user_id"],
                min_importance=3
            )
            
            state["long_term_memories"] = important_memories
            
            logger.info(f"Loaded {len(recent_messages)} recent messages and {len(important_memories)} memories")
            
        except Exception as e:
            logger.error(f"Error in load_memory: {e}")
            state["short_term_context"] = {"recent_messages": [], "message_count": 0}
            state["long_term_memories"] = []
        
        return state
    
    def retrieve_context(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """
        Retrieve relevant documents from the knowledge base.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with retrieved documents
        """
        logger.info("Node: retrieve_context")
        
        if not state.get("needs_retrieval", True):
            logger.info("Skipping retrieval - not needed")
            state["retrieved_documents"] = []
            state["context_string"] = ""
            return state
        
        try:
            result = self.rag.retrieve(
                query=state["user_input"],
                current_stage=state["current_stage"],
                top_k=5,
                use_reranking=True
            )
            
            state["retrieved_documents"] = result["documents"]
            state["context_string"] = self.rag.get_context_string(result["documents"])
            
            sources = []
            for doc in result["documents"]:
                sources.append({
                    "source": doc.metadata.get("source", "unknown"),
                    "category": doc.metadata.get("category", "general"),
                    "score": doc.metadata.get("score", 0.0),
                    "preview": doc.page_content[:150] + "..."
                })
            
            state["sources"] = sources
            
            logger.info(f"Retrieved {len(result['documents'])} documents")
            
        except Exception as e:
            logger.error(f"Error in retrieve_context: {e}")
            state["retrieved_documents"] = []
            state["context_string"] = ""
            state["sources"] = []
        
        return state
    
    def generate_response(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """
        Generate response using LLM with context and memories.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with generated response
        """
        logger.info("Node: generate_response")
        
        try:
            stage_prompts = {
                "welcome": "You are greeting a new user. Be warm, welcoming, and provide an overview.",
                "profile_setup": "You are helping the user set up their profile. Guide them through the process.",
                "learning_preferences": "You are learning about the user's preferences and needs.",
                "first_steps": "You are guiding the user through their first actions on the platform.",
                "completed": "The user has completed onboarding. Offer ongoing support and advanced features."
            }
            
            context_section = ""
            if state.get("context_string"):
                context_section = f"\n\nRelevant Documentation:\n{state['context_string']}\n"
            
            memory_section = ""
            if state.get("long_term_memories"):
                memory_items = [f"- {m['key']}: {m['value']}" for m in state["long_term_memories"][:3]]
                memory_section = f"\n\nUser Preferences:\n" + "\n".join(memory_items) + "\n"
            
            system_prompt = f"""You are a friendly onboarding assistant for TechVenture Solutions.

Current Onboarding Stage: {state['current_stage']}
{stage_prompts.get(state['current_stage'], '')}

Guidelines:
- Be helpful, concise, and encouraging
- Use the provided documentation to give accurate answers
- Reference sources when providing specific information
- Adapt your tone to the user's onboarding stage
- If you don't know something, admit it and offer to help find the answer
{context_section}{memory_section}"""
            
            messages = [SystemMessage(content=system_prompt)]
            
            recent_messages = state.get("short_term_context", {}).get("recent_messages", [])
            for msg in recent_messages[-3:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=state["user_input"]))
            
            response = self.llm.invoke(messages)
            state["response"] = response.content
            
            logger.info("Generated response successfully")
            
        except Exception as e:
            logger.error(f"Error in generate_response: {e}")
            state["response"] = "I apologize, but I encountered an error generating a response. Please try again."
            state["error"] = str(e)
        
        return state
    
    def save_memory(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """
        Save conversation to memory systems.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        logger.info("Node: save_memory")
        
        try:
            self.short_term_memory.save_message(
                state["session_id"],
                "user",
                state["user_input"]
            )
            
            self.short_term_memory.save_message(
                state["session_id"],
                "assistant",
                state["response"]
            )
            
            db = next(get_db())
            ltm = LongTermMemory(db)
            
            ltm.update_onboarding_progress(
                state["user_id"],
                state["current_stage"],
                f"conversation_{state['session_id'][:8]}"
            )
            
            logger.info("Saved conversation to memory")
            
        except Exception as e:
            logger.error(f"Error in save_memory: {e}")
        
        return state
