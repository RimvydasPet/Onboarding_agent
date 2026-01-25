from langgraph.graph import StateGraph, END
from backend.agent.state import OnboardingAgentState
from backend.agent.nodes import AgentNodes
import logging

logger = logging.getLogger(__name__)


def create_onboarding_agent():
    """Create the LangGraph agent for onboarding."""
    
    nodes = AgentNodes()
    
    workflow = StateGraph(OnboardingAgentState)
    
    workflow.add_node("analyze_input", nodes.analyze_input)
    workflow.add_node("load_memory", nodes.load_memory)
    workflow.add_node("retrieve_context", nodes.retrieve_context)
    workflow.add_node("generate_response", nodes.generate_response)
    workflow.add_node("save_memory", nodes.save_memory)
    
    workflow.set_entry_point("analyze_input")
    
    workflow.add_edge("analyze_input", "load_memory")
    workflow.add_edge("load_memory", "retrieve_context")
    workflow.add_edge("retrieve_context", "generate_response")
    workflow.add_edge("generate_response", "save_memory")
    workflow.add_edge("save_memory", END)
    
    app = workflow.compile()
    
    logger.info("Onboarding agent graph created")
    return app


def run_agent(user_input: str, user_id: int = 1, session_id: str = "default", current_stage: str = "welcome"):
    """
    Run the onboarding agent with user input.
    
    Args:
        user_input: User's message
        user_id: User ID
        session_id: Session ID
        current_stage: Current onboarding stage
    
    Returns:
        Agent response with sources
    """
    from langchain_core.messages import HumanMessage
    
    app = create_onboarding_agent()
    
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_input": user_input,
        "user_id": user_id,
        "session_id": session_id,
        "current_stage": current_stage,
        "query_analysis": None,
        "retrieved_documents": [],
        "context_string": "",
        "short_term_context": None,
        "long_term_memories": [],
        "response": "",
        "sources": [],
        "needs_retrieval": True,
        "error": None
    }
    
    try:
        result = app.invoke(initial_state)
        
        return {
            "response": result.get("response", "I apologize, but I couldn't generate a response."),
            "sources": result.get("sources", []),
            "stage": current_stage,
            "session_id": session_id
        }
    
    except Exception as e:
        logger.error(f"Error running agent: {e}")
        return {
            "response": f"I apologize, but I encountered an error: {str(e)}",
            "sources": [],
            "stage": current_stage,
            "session_id": session_id
        }
