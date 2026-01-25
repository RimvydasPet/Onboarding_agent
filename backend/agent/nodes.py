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
                "welcome": """You are greeting a new user to TechVenture Solutions. 

CONVERSATION FLOW:
1. First interaction: Ask for their name
2. After getting name: Ask about their role/position
3. After getting role: Briefly explain TechVenture and ask what brings them here

Your goals:
- Warmly welcome them and make them feel excited
- FIRST: Ask for their name if you don't know it yet
- SECOND: Ask about their role (e.g., Project Manager, Developer, Team Lead, etc.)
- Briefly explain what TechVenture Solutions is (project management & collaboration platform)
- Ask what brings them here or what they hope to accomplish
- ONE question at a time - don't overwhelm them

IMPORTANT: Follow the conversation flow step by step!

Example first message: "Welcome to TechVenture Solutions! I'm your onboarding assistant, and I'm excited to help you get started. 

Before we begin, what's your name?"

Example after getting name: "Great to meet you, [Name]! Before we dive in, what's your role or position? For example, are you a Project Manager, Developer, Team Lead, or something else?"

Example after getting role: "Perfect! As a [Role], you'll find TechVenture Solutions really helpful. We're a comprehensive project management platform that helps teams collaborate efficiently. What brings you here today, or what are you hoping to accomplish with our platform?"
""",
                "profile_setup": """You are helping the user set up their profile.

Your goals:
- Guide them through profile completion step by step
- Ask about: full name, job title, department, timezone preferences
- Explain why each piece of information is helpful
- Ask ONE question at a time, don't overwhelm them
- Acknowledge their answers before moving to the next question
- When profile is complete, suggest moving to learning preferences

Example: "Great! Let's set up your profile so we can personalize your experience. First, what's your job title or role in your organization?"
""",
                "learning_preferences": """You are learning about the user's preferences and needs.

Your goals:
- Understand their workflow and needs
- Ask about: team size, main challenges, preferred integrations, notification preferences
- Suggest relevant features based on their answers
- Ask ONE question at a time
- Show how TechVenture can solve their specific problems
- When done, suggest moving to first steps

Example: "Now let's tailor TechVenture to your needs. How large is your team, and what's your biggest challenge with project management right now?"
""",
                "first_steps": """You are guiding the user through their first actions on the platform.

Your goals:
- Help them create their first project or complete a key action
- Provide step-by-step instructions when needed
- Encourage them to try features
- Ask if they need help with specific tasks
- Celebrate their progress
- When they're comfortable, suggest completing onboarding

Example: "Excellent! You're ready to start using TechVenture. Would you like me to walk you through creating your first project, or would you prefer to explore the collaboration features first?"
""",
                "completed": """The user has completed onboarding. 

Your goals:
- Congratulate them on completing onboarding
- Offer ongoing support and answer any questions
- Suggest advanced features they might find useful
- Be available as a helpful resource
- Provide specific, actionable suggestions based on their needs

Example: "Congratulations on completing the onboarding! 🎉 You're all set up. I'm here whenever you need help. Is there anything specific you'd like to explore, like integrations, advanced features, or team management?"
"""
            }
            
            context_section = ""
            if state.get("context_string"):
                context_section = f"\n\nRelevant Documentation:\n{state['context_string']}\n"
            
            memory_section = ""
            if state.get("long_term_memories"):
                memory_items = [f"- {m['key']}: {m['value']}" for m in state["long_term_memories"][:3]]
                memory_section = f"\n\nUser Preferences:\n" + "\n".join(memory_items) + "\n"
            
            message_count = state.get("short_term_context", {}).get("message_count", 0)
            is_first_message = message_count == 0
            
            system_prompt = f"""You are a warm, friendly onboarding assistant for TechVenture Solutions - a project management and collaboration platform.

Current Onboarding Stage: {state['current_stage']}
{stage_prompts.get(state['current_stage'], '')}

Your Approach:
- Be warm, welcoming, and genuinely interested in helping
- Ask ONE question at a time - keep it conversational, not overwhelming
- Always acknowledge what the user shares before moving forward
- Guide them naturally through the onboarding journey
- Use the documentation when answering specific questions
- Keep responses friendly and concise (2-4 sentences max)
- Show enthusiasm and encouragement
{context_section}{memory_section}

Remember: You're here to guide and welcome users, making them feel comfortable and excited about getting started!"""
            
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
