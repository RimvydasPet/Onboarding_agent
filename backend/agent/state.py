from typing import TypedDict, List, Dict, Any, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class OnboardingAgentState(TypedDict):
    """State for the onboarding agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: int
    session_id: str
    current_stage: str
    user_context: Dict[str, Any]
    retrieved_docs: List[Dict[str, Any]]
    next_action: str
    should_retrieve: bool
    query_analysis: Dict[str, Any]
