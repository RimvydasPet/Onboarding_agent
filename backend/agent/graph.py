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
        Agent response
    """
    from langchain_core.messages import HumanMessage
    
    agent = create_onboarding_agent()
    
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_id": user_id,
        "session_id": session_id,
        "current_stage": current_stage,
        "user_context": {},
        "retrieved_docs": [],
        "next_action": "",
        "should_retrieve": False,
        "query_analysis": {}
    }
    
    result = agent.invoke(initial_state)
    
    last_message = result["messages"][-1]
    response = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    return {
        "response": response,
        "retrieved_docs": result.get("retrieved_docs", []),
        "query_analysis": result.get("query_analysis", {}),
        "current_stage": result.get("current_stage", current_stage)
    }
