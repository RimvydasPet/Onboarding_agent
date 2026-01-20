from typing import Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.agent.state import OnboardingAgentState
from backend.rag.agentic_rag import AgenticRAG
from backend.memory.short_term import ShortTermMemory
from backend.memory.long_term import LongTermMemory
from backend.services.task_manager import TaskManager
from backend.config import settings
from backend.database.connection import get_db
import logging

logger = logging.getLogger(__name__)


class AgentNodes:
    """Node functions for the LangGraph agent."""
    
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.7
        )
        self.rag = AgenticRAG()
        self.short_term_memory = ShortTermMemory()
    
    def analyze_input(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """Analyze user input and determine if retrieval is needed."""
        last_message = state["messages"][-1]
        user_query = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        context = {
            "current_stage": state.get("current_stage", "welcome"),
            "user_context": state.get("user_context", {})
        }
        
        result = self.rag.retrieve(user_query, context, top_k=3)
        
        state["should_retrieve"] = result["retrieval_performed"]
        state["query_analysis"] = result.get("analysis", {})
        
        if result["retrieval_performed"]:
            state["retrieved_docs"] = result["citations"]
        else:
            state["retrieved_docs"] = []
        
        logger.info(f"Analysis complete. Retrieval needed: {state['should_retrieve']}")
        return state
    
    def retrieve_context(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """Retrieve relevant context from RAG system."""
        if not state.get("should_retrieve", False):
            logger.info("Skipping retrieval - not needed")
            return state
        
        logger.info(f"Retrieved {len(state['retrieved_docs'])} documents")
        return state
    
    def load_memory(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """Load relevant memories for the conversation."""
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id", 1)
        
        recent_messages = self.short_term_memory.get_messages(session_id, limit=5)
        context = self.short_term_memory.get_context(session_id)
        
        db = next(get_db())
        ltm = LongTermMemory(db)
        important_memories = ltm.get_important_memories(user_id, min_importance=3, limit=5)
        onboarding_progress = ltm.get_onboarding_progress(user_id)
        
        state["user_context"] = {
            "recent_messages": recent_messages,
            "session_context": context,
            "important_memories": important_memories,
            "onboarding_progress": onboarding_progress
        }
        
        logger.info(f"Loaded memories: {len(recent_messages)} recent messages, {len(important_memories)} important memories")
        return state
    
    def generate_response(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """Generate response using LLM with context."""
        last_message = state["messages"][-1]
        user_query = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        system_prompt = self._build_system_prompt(state)
        context_prompt = self._build_context_prompt(state)
        
        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=context_prompt),
            HumanMessage(content=user_query)
        ]
        
        response = self.llm.invoke(messages)
        
        state["messages"].append(AIMessage(content=response.content))
        
        logger.info("Response generated")
        return state
    
    def save_memory(self, state: OnboardingAgentState) -> OnboardingAgentState:
        """Save conversation to memory."""
        session_id = state.get("session_id", "default")
        user_id = state.get("user_id", 1)
        
        if len(state["messages"]) >= 2:
            user_msg = state["messages"][-2]
            ai_msg = state["messages"][-1]
            
            if hasattr(user_msg, 'content'):
                self.short_term_memory.save_message(
                    session_id, "user", user_msg.content,
                    metadata={"stage": state.get("current_stage")}
                )
            
            if hasattr(ai_msg, 'content'):
                self.short_term_memory.save_message(
                    session_id, "assistant", ai_msg.content,
                    metadata={"stage": state.get("current_stage")}
                )
        
        self.short_term_memory.update_context(session_id, {
            "last_stage": state.get("current_stage"),
            "last_query_analysis": state.get("query_analysis", {})
        })
        
        logger.info("Conversation saved to memory")
        return state
    
    def _build_system_prompt(self, state: OnboardingAgentState) -> str:
        """Build system prompt for the agent."""
        stage = state.get("current_stage", "welcome")
        user_id = state.get("user_id", 1)
        
        # Get task information
        db = next(get_db())
        task_manager = TaskManager(db)
        task_manager.initialize_stage_tasks(user_id, stage)
        
        progress = task_manager.get_stage_progress(user_id, stage)
        next_task = task_manager.get_next_incomplete_task(user_id, stage)
        
        base_prompt = """You are a proactive onboarding assistant. Your PRIMARY goal is to guide users through specific tasks to complete their onboarding.

Your responsibilities:
- PROACTIVELY guide users through required tasks
- ASK questions to collect necessary information
- VALIDATE user responses before marking tasks complete
- ENCOURAGE users and celebrate task completions
- SUGGEST the next task after each completion
- Be directive but friendly

Communication style:
- Start by asking questions, not just answering
- Guide users step-by-step through tasks
- Be specific about what you need from them
- Acknowledge task completion explicitly
- Always suggest the next action"""

        stage_prompts = {
            "welcome": f"""\n\nCurrent Stage: WELCOME ({progress['required_completed']}/{progress['required_total']} required tasks complete)

Your goal: Collect basic information and set expectations.
Required tasks:
- Get user's name
- Understand their role
- Explain what they'll accomplish

Start by warmly greeting them and asking for their name.""",
            "profile_setup": f"""\n\nCurrent Stage: PROFILE SETUP ({progress['required_completed']}/{progress['required_total']} required tasks complete)

Your goal: Help complete their profile with all required information.
Required tasks:
- Full name
- Email verification
- Role selection

Ask for each piece of information one at a time. Validate before moving on.""",
            "learning_preferences": f"""\n\nCurrent Stage: LEARNING PREFERENCES ({progress['required_completed']}/{progress['required_total']} required tasks complete)

Your goal: Understand how they prefer to learn.
Required tasks:
- Learning style (visual/hands-on/reading)
- Notification preferences
- Tutorial pace

Present options clearly and ask them to choose.""",
            "first_steps": f"""\n\nCurrent Stage: FIRST STEPS ({progress['required_completed']}/{progress['required_total']} required tasks complete)

Your goal: Guide them through initial platform actions.
Required tasks:
- Explore dashboard
- Create first project
- Complete tutorial

Provide clear instructions for each task. Ask them to confirm completion.""",
            "completed": f"""\n\nCurrent Stage: COMPLETED

Congratulate them on completing onboarding! Offer ongoing support and suggest next steps for continued learning."""
        }
        
        prompt = base_prompt + stage_prompts.get(stage, "")
        
        # Add current task focus
        if next_task:
            task_type = "Optional" if next_task["optional"] else "Required"
            prompt += f"\n\nCURRENT TASK ({task_type}): {next_task['description']}\nFocus on completing this task with the user."
        elif progress['stage_complete']:
            prompt += "\n\nAll required tasks complete! Congratulate the user and let them know they can move to the next stage."
        
        return prompt
    
    def _build_context_prompt(self, state: OnboardingAgentState) -> str:
        """Build context prompt with retrieved documents and memories."""
        parts = []
        
        if state.get("retrieved_docs"):
            parts.append("Relevant Documentation:")
            for i, doc in enumerate(state["retrieved_docs"][:3], 1):
                parts.append(f"\n[Source {i}]: {doc['content'][:300]}...")
        
        user_context = state.get("user_context", {})
        if user_context.get("onboarding_progress"):
            progress = user_context["onboarding_progress"]
            parts.append(f"\n\nUser Progress:")
            parts.append(f"- Current Stage: {progress.get('current_stage', 'unknown')}")
            parts.append(f"- Completed Steps: {len(progress.get('completed_steps', []))}")
        
        if user_context.get("important_memories"):
            parts.append("\n\nUser Preferences:")
            for memory in user_context["important_memories"][:3]:
                parts.append(f"- {memory['key']}: {memory['value']}")
        
        return "\n".join(parts) if parts else "No additional context available."
