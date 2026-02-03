from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage


class OnboardingAgentState(TypedDict):
    """State for the onboarding agent workflow."""
    
    messages: List[BaseMessage]
    user_input: str
    user_id: int
    session_id: str
    current_stage: str
    
    query_analysis: Optional[Dict[str, Any]]
    retrieved_documents: List[Any]
    context_string: str
    
    short_term_context: Optional[Dict[str, Any]]
    long_term_memories: List[Dict[str, Any]]
    onboarding_facts: Dict[str, Any]

    generated_question_bank: Dict[str, Any]
    onboarding_checklist: List[str]
    role_research: Dict[str, Any]
    
    response: str
    sources: List[Dict[str, Any]]

    next_stage: Optional[str]
    extracted_facts: Dict[str, Any]
    
    needs_retrieval: bool
    error: Optional[str]
