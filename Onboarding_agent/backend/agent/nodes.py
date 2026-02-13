from typing import Dict, Any
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
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

    _STAGE_FIELDS: Dict[str, list[tuple[str, str]]] = {
        "welcome": [
            ("name", "Before we begin, what's your name?"),
            ("role", "Great—what's your role or position? (e.g., IT Admin, Developer, Project Manager)"),
            # Everything after role is role-based (see _ROLE_STAGE_FIELDS)
        ],
        "profile_setup": [],
        "learning_preferences": [],
        "first_steps": [],
        "completed": []
    }

    _STAGE_ORDER = ["welcome", "profile_setup", "learning_preferences", "first_steps", "completed"]

    _STAGE_INTRODUCTIONS: Dict[str, str] = {
        "profile_setup": (
            "🎯 **Profile Setup**\n\n"
            "Now let's set up your profile! This helps us personalize your experience and ensures "
            "your teammates can easily find and collaborate with you. A complete profile also helps "
            "route approvals and support requests to the right people."
        ),
        "learning_preferences": (
            "📚 **Learning Preferences**\n\n"
            "Let's understand how you work best! This stage helps us tailor TechVenture Solutions to your "
            "workflow, recommend the right integrations, and set up notifications that work for you — "
            "not against you. The better we understand your needs, the more productive you'll be."
        ),
        "first_steps": (
            "🚀 **First Steps**\n\n"
            "Time to take action! In this stage, we'll make sure you have everything you need to hit "
            "the ground running — from account access to creating your first project. This is where "
            "onboarding becomes real and you start seeing TechVenture Solutions in action."
        ),
        "completed": (
            "🎉 **Onboarding Complete!**\n\n"
            "Congratulations — you've finished onboarding! You're now fully set up and ready to make "
            "the most of TechVenture Solutions. I'm still here whenever you need help with advanced "
            "features, integrations, or anything else."
        )
    }

    @staticmethod
    def _normalize_stage_key(stage: str) -> str:
        return str(stage or "welcome")

    @staticmethod
    def _deduplicate_name(name: str) -> str:
        """Remove accidental name doubling like 'RimvydasRimvydas' -> 'Rimvydas'."""
        if not name:
            return name
        name = name.strip()
        # Check for exact doubling: "NameName"
        length = len(name)
        if length >= 2 and length % 2 == 0:
            half = length // 2
            if name[:half].lower() == name[half:].lower():
                return name[:half]
        # Check for doubling with space: "Name Name"
        parts = name.split()
        if len(parts) == 2 and parts[0].lower() == parts[1].lower():
            return parts[0]
        return name

    @classmethod
    def _next_stage_for(cls, stage: str) -> str | None:
        stage = cls._normalize_stage_key(stage)
        try:
            idx = cls._STAGE_ORDER.index(stage)
        except ValueError:
            return None
        if idx + 1 < len(cls._STAGE_ORDER):
            return cls._STAGE_ORDER[idx + 1]
        return None

    @staticmethod
    def _facts_from_memories(memories: list[dict[str, Any]]) -> Dict[str, Any]:
        facts: Dict[str, Any] = {}
        for m in memories or []:
            if m.get("type") != "onboarding":
                continue
            k = m.get("key")
            if not k:
                continue
            facts[str(k)] = m.get("value")
        return facts

    @classmethod
    def _role_category(cls, role: Any) -> str:
        text = str(role or "").strip().lower()
        if any(k in text for k in ["dev", "engineer", "developer", "software"]):
            return "developer"
        if any(k in text for k in ["pm", "project manager", "product", "scrum"]):
            return "pm"
        if any(k in text for k in ["it", "admin", "administrator"]):
            return "it_admin"
        return "general"

    @staticmethod
    def _normalize_role(role: Any) -> str:
        return re.sub(r"\s+", " ", str(role or "").strip().lower())

    @classmethod
    def _generated_bank_cache_key(cls, role: Any, stage: str) -> str:
        stage = cls._normalize_stage_key(stage)
        return f"generated_question_bank.role:{cls._normalize_role(role)}.stage:{stage}"

    @classmethod
    def _generated_checklist_cache_key(cls, role: Any) -> str:
        return f"onboarding_checklist.role:{cls._normalize_role(role)}"

    @classmethod
    def _role_research_cache_key(cls, role: Any, stage: str) -> str:
        stage = cls._normalize_stage_key(stage)
        return f"role_research.role:{cls._normalize_role(role)}.stage:{stage}"

    @classmethod
    def _missing_fields(
        cls,
        stage: str,
        facts: Dict[str, Any],
        generated_question_bank: Dict[str, Any] | None = None,
    ) -> list[tuple[str, str]]:
        stage = cls._normalize_stage_key(stage)
        missing: list[tuple[str, str]] = []

        fields: list[tuple[str, str]] = list(cls._STAGE_FIELDS.get(stage, []))

        if stage != "welcome":
            stage_bank = None
            if isinstance(generated_question_bank, dict):
                stage_bank = generated_question_bank.get(stage)

            if isinstance(stage_bank, list) and stage_bank:
                for idx, item in enumerate(stage_bank, start=1):
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        field_key, question = item
                    elif isinstance(item, dict):
                        field_key = item.get("field") or item.get("key") or f"q{idx}"
                        question = item.get("question") or item.get("text") or ""
                    else:
                        field_key, question = f"q{idx}", str(item)

                    field_key = str(field_key or f"q{idx}")
                    question = str(question or "").strip()
                    if question:
                        fields.append((field_key, question))

        for field_key, question in fields:
            namespaced = f"{stage}.{field_key}"
            if namespaced not in facts or facts.get(namespaced) in (None, ""):
                missing.append((field_key, question))
        return missing

    def _tavily_search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        api_key = str(getattr(settings, "TAVILY_API_KEY", "") or "").strip()
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured")

        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        req = urllib.request.Request(
            url="https://api.tavily.com/search",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Tavily HTTP error: {getattr(e, 'code', '?')}") from e
        except Exception as e:
            raise RuntimeError("Tavily request failed") from e

        results = data.get("results")
        if not isinstance(results, list):
            return []
        cleaned: list[dict[str, Any]] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            cleaned.append(
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": r.get("content"),
                    "score": r.get("score"),
                }
            )
        return cleaned

    def _generate_role_question_bank_from_research(self, role: str, stage: str, research_results: list[dict[str, Any]]) -> dict[str, Any]:
        results_text_parts: list[str] = []
        for idx, r in enumerate(research_results or [], start=1):
            if not isinstance(r, dict):
                continue
            title = str(r.get("title") or "").strip()
            url = str(r.get("url") or "").strip()
            content = str(r.get("content") or "").strip()
            if not (title or url or content):
                continue
            results_text_parts.append(
                f"[{idx}] {title}\nURL: {url}\nSnippet: {content}".strip()
            )

        research_block = "\n\n".join(results_text_parts)[:12000]

        stage = self._normalize_stage_key(stage)

        prompt = f"""You are creating a role-specific onboarding plan for a new hire.

ROLE: {role}
STAGE: {stage}

Use the following web research snippets as background:
{research_block}

Return ONLY valid JSON with this schema:
{{
  "onboarding_checklist": ["..."],
  "questions": [{{"field": "q1", "question": "..."}}]
}}

Rules:
- Provide 5-10 checklist items relevant to the role (can be general, not stage-specific).
- Provide 3-5 questions ONLY for the given STAGE.
- Questions must be specific to the role and phrased conversationally.
- Do NOT generate questions for the welcome stage (name/role are handled separately).
"""

        if not str(prompt or "").strip():
            raise ValueError("contents are required")

        # Some Gemini backends reject SystemMessage-only inputs; provide the prompt as user content.
        response = self.llm.invoke([HumanMessage(content=prompt)])
        raw = (response.content or "").strip()

        if not raw:
            raise RuntimeError("Gemini returned empty content")

        # Be tolerant to code fences or leading/trailing text.
        cleaned = raw
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```\s*$", "", cleaned)
            cleaned = cleaned.strip()

        # Try direct parse first.
        try:
            data = json.loads(cleaned)
        except Exception:
            # Fallback: extract first JSON object in the text.
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                preview = cleaned[:400].replace("\n", "\\n")
                raise RuntimeError(f"Gemini did not return JSON. Output preview: {preview}")
            candidate = cleaned[start : end + 1]
            try:
                data = json.loads(candidate)
            except Exception as e:
                preview = candidate[:400].replace("\n", "\\n")
                raise RuntimeError(f"Gemini returned invalid JSON: {type(e).__name__}. JSON preview: {preview}")

        if not isinstance(data, dict):
            raise RuntimeError("Question bank generation returned non-object JSON")

        return data

    def _ensure_generated_question_bank(self, state: OnboardingAgentState, stage: str) -> None:
        facts = state.get("onboarding_facts") or {}
        role_value = facts.get("welcome.role")
        role = self._normalize_role(role_value)
        if not role:
            return

        stage = self._normalize_stage_key(stage)
        if stage in ("welcome", "completed"):
            return

        # Dynamic question generation requires an LLM provider.
        google_key = str(getattr(settings, "GOOGLE_API_KEY", "") or "").strip()
        if not google_key:
            raise RuntimeError("GOOGLE_API_KEY is not configured")

        existing_bank = state.get("generated_question_bank")
        if not isinstance(existing_bank, dict):
            existing_bank = {}
            state["generated_question_bank"] = existing_bank

        if isinstance(existing_bank.get(stage), list) and existing_bank.get(stage):
            return

        db = next(get_db())
        ltm = LongTermMemory(db)

        checklist_key = self._generated_checklist_cache_key(role)
        bank_key = self._generated_bank_cache_key(role, stage)
        research_key = self._role_research_cache_key(role, stage)

        cached_bank = ltm.get_memory(state["user_id"], "onboarding_generated", bank_key)
        cached_checklist = ltm.get_memory(state["user_id"], "onboarding_generated", checklist_key)
        cached_research = ltm.get_memory(state["user_id"], "onboarding_generated", research_key)

        if isinstance(cached_bank, list) and cached_bank:
            existing_bank[stage] = cached_bank
            if isinstance(cached_checklist, list):
                state["onboarding_checklist"] = cached_checklist
            if isinstance(cached_research, dict):
                role_research = state.get("role_research")
                if not isinstance(role_research, dict):
                    role_research = {}
                role_research[stage] = cached_research
                state["role_research"] = role_research
            return

        provider = str(getattr(settings, "WEB_SEARCH_PROVIDER", "tavily") or "tavily").strip().lower()
        research_results: list[dict[str, Any]] = []
        search_error = None
        if provider == "tavily":
            try:
                research_results = self._tavily_search(f"{role} onboarding questions {stage}", max_results=6)
            except Exception as e:
                search_error = str(e)
                logger.warning(f"Web search failed: {e}")
                raise RuntimeError(search_error or "Tavily web search failed") from e
        else:
            raise RuntimeError(f"Unsupported WEB_SEARCH_PROVIDER: {provider}")

        try:
            generated_payload = self._generate_role_question_bank_from_research(role=role, stage=stage, research_results=research_results)
        except Exception as e:
            logger.warning(f"Question bank generation failed: {e}")
            raise

        stage_questions = generated_payload.get("questions")
        generated_checklist = generated_payload.get("onboarding_checklist")

        if not isinstance(stage_questions, list) or not stage_questions:
            raise RuntimeError("questions missing from generation payload")

        existing_bank[stage] = stage_questions
        state["onboarding_checklist"] = generated_checklist if isinstance(generated_checklist, list) else []

        role_research = state.get("role_research")
        if not isinstance(role_research, dict):
            role_research = {}
        role_research[stage] = {
            "provider": provider,
            "query": f"{role} onboarding questions {stage}",
            "results": research_results,
            "generated_at": datetime.utcnow().isoformat(),
            "error": search_error,
        }
        state["role_research"] = role_research

        ltm.save_memory(
            user_id=state["user_id"],
            memory_type="onboarding_generated",
            key=bank_key,
            value=stage_questions,
            importance=3,
        )
        ltm.save_memory(
            user_id=state["user_id"],
            memory_type="onboarding_generated",
            key=checklist_key,
            value=state["onboarding_checklist"],
            importance=3,
        )
        ltm.save_memory(
            user_id=state["user_id"],
            memory_type="onboarding_generated",
            key=research_key,
            value=role_research.get(stage),
            importance=2,
        )

    @staticmethod
    def _tailored_guidance(stage: str, field_key: str, value: Any) -> str:
        stage = str(stage or "")
        field_key = str(field_key or "")
        text = str(value or "").strip()
        low = text.lower()

        if stage == "welcome" and field_key == "role":
            if any(k in low for k in ["dev", "engineer", "developer", "software"]):
                return "Nice — I’ll tailor examples toward developer workflows (projects, tasks, integrations, and permissions)."
            if any(k in low for k in ["pm", "project manager", "product", "scrum"]):
                return "Great — I’ll focus on planning, milestones, reporting, and stakeholder collaboration."
            if any(k in low for k in ["it", "admin", "administrator"]):
                return "Perfect — I’ll emphasize workspace setup, access, permissions, and integrations." 

        if stage == "welcome" and field_key == "location":
            if "remote" in low:
                return "Noted — I’ll include remote-friendly tips (async updates, notification setup, and collaboration routines)."

        if stage == "profile_setup" and field_key == "timezone":
            return "Got it — I’ll align reminders and suggested working hours to your timezone."

        if stage == "learning_preferences" and field_key == "learning_style":
            if "hands" in low or "walk" in low:
                return "Great — I’ll give you short step-by-step walkthroughs you can follow immediately."
            if "video" in low:
                return "Great — I’ll keep guidance in short, digestible chunks and point you to relevant materials."
            if "doc" in low:
                return "Great — I’ll keep answers structured and reference documentation sections when possible."

        if stage == "learning_preferences" and field_key == "integrations":
            if "slack" in low:
                return "If Slack is important, we’ll prioritize notifications + project updates routing there."
            if "jira" in low:
                return "If Jira is in your workflow, we’ll map projects/tasks so updates stay consistent across tools."
            if any(k in low for k in ["google", "workspace", "gmail", "calendar"]):
                return "If Google Workspace is key, we’ll focus on calendar alignment and sharing/access patterns."

        if stage == "first_steps" and field_key == "accounts_access":
            if any(k in low for k in ["missing", "no", "not", "don\u2019t", "dont"]):
                return "Thanks — we should unblock access first. I can help you list exactly what to request (accounts, permissions, and who typically approves)."

        return ""
    
    def __init__(self):
        """Initialize agent nodes with required components."""
        self.rag = AgenticRAG()
        self.short_term_memory = ShortTermMemory()
        self.llm = ChatGoogleGenerativeAI(
            model=str(getattr(settings, "gemini_model_id", None) or getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash-latest") or "gemini-1.5-flash-latest"),
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
            existing_ctx = state.get("short_term_context") or {}
            existing_recent = existing_ctx.get("recent_messages") or []

            recent_messages = self.short_term_memory.get_messages(
                state["session_id"],
                limit=5
            )

            merged_recent = recent_messages if recent_messages else existing_recent
            state["short_term_context"] = {
                "recent_messages": merged_recent,
                "message_count": len(merged_recent)
            }
            
            db = next(get_db())
            ltm = LongTermMemory(db)

            important_memories = ltm.get_important_memories(state["user_id"], min_importance=3)
            state["long_term_memories"] = important_memories

            onboarding_memories = ltm.get_memories_by_type(state["user_id"], "onboarding")
            onboarding_facts = {}
            for mem in onboarding_memories or []:
                if mem.get("key"):
                    onboarding_facts[str(mem["key"])] = mem.get("value")

            # Deduplicate name if stored doubled
            if isinstance(onboarding_facts.get("welcome.name"), str):
                onboarding_facts["welcome.name"] = self._deduplicate_name(
                    str(onboarding_facts.get("welcome.name") or "")
                )

            # Also fix the name in long_term_memories list for LLM context
            for mem in important_memories:
                if mem.get("key") == "welcome.name" and isinstance(mem.get("value"), str):
                    mem["value"] = self._deduplicate_name(str(mem["value"]))

            state["onboarding_facts"] = onboarding_facts

            role_value = onboarding_facts.get("welcome.role")
            if role_value:
                checklist_key = self._generated_checklist_cache_key(role_value)
                cached_bank = None
                cached_checklist = ltm.get_memory(state["user_id"], "onboarding_generated", checklist_key)
                cached_research = None

                # Per-stage caches: attempt to load any stage question lists already generated.
                stage_banks: Dict[str, Any] = {}
                stage_research: Dict[str, Any] = {}
                for stage_key in ["profile_setup", "learning_preferences", "first_steps"]:
                    bank_key = self._generated_bank_cache_key(role_value, stage_key)
                    research_key = self._role_research_cache_key(role_value, stage_key)
                    cached_bank = ltm.get_memory(state["user_id"], "onboarding_generated", bank_key)
                    cached_research = ltm.get_memory(state["user_id"], "onboarding_generated", research_key)
                    if isinstance(cached_bank, list) and cached_bank:
                        stage_banks[stage_key] = cached_bank
                    if isinstance(cached_research, dict) and cached_research:
                        stage_research[stage_key] = cached_research

                if stage_banks:
                    state["generated_question_bank"] = stage_banks
                if isinstance(cached_checklist, list):
                    state["onboarding_checklist"] = cached_checklist
                if stage_research:
                    state["role_research"] = stage_research
            
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
            current_stage = self._normalize_stage_key(state.get("current_stage"))
            onboarding_facts = dict(state.get("onboarding_facts") or {})

            qa_pending_stage = str(onboarding_facts.get("qa.pending_stage") or "").strip()
            user_text = str(state.get("user_input") or "").strip()
            user_low = user_text.lower()
            user_wants_move_on = any(
                phrase in user_low
                for phrase in [
                    "move on",
                    "next stage",
                    "continue",
                    "go next",
                    "proceed",
                    "lets move on",
                    "let's move on",
                    "ok move on",
                    "yes move on",
                ]
            )
            if current_stage != "welcome":
                try:
                    self._ensure_generated_question_bank(state, current_stage)
                except Exception as e:
                    state["response"] = (
                        "I can't generate role-based onboarding questions right now because the web-search/question-generation "
                        f"step failed: {type(e).__name__}: {e}\n\n"
                        "Please check:\n"
                        "- TAVILY_API_KEY is set\n"
                        "- GOOGLE_API_KEY is set\n"
                        "- GEMINI_MODEL is valid (e.g. models/gemini-2.0-flash)\n"
                        "Then restart the app and click '🔄 New Session'."
                    )
                    state["next_stage"] = None
                    state["extracted_facts"] = {}
                    state["onboarding_facts"] = onboarding_facts
                    return state

            # If the user is in the post-stage Q&A mode for the current stage, only move on when they confirm.
            if qa_pending_stage and qa_pending_stage == current_stage:
                if user_wants_move_on:
                    # Clear the pending stage and advance.
                    state["extracted_facts"] = {"qa.pending_stage": ""}
                    onboarding_facts["qa.pending_stage"] = ""
                    state["onboarding_facts"] = onboarding_facts

                    next_stage = self._next_stage_for(current_stage)
                    if next_stage and next_stage != "completed":
                        state["next_stage"] = next_stage
                        try:
                            self._ensure_generated_question_bank(state, next_stage)
                        except Exception as e:
                            state["response"] = (
                                "I can't generate role-based onboarding questions for the next stage because the web-search/question-generation "
                                f"step failed: {type(e).__name__}: {e}\n\n"
                                "Please check:\n"
                                "- TAVILY_API_KEY is set\n"
                                "- GOOGLE_API_KEY is set\n"
                                "- GEMINI_MODEL is valid (e.g. models/gemini-2.0-flash)"
                            )
                            return state

                        next_stage_missing = self._missing_fields(
                            next_stage,
                            onboarding_facts,
                            generated_question_bank=state.get("generated_question_bank"),
                        )
                        if next_stage_missing:
                            stage_intro = self._STAGE_INTRODUCTIONS.get(next_stage, "")
                            next_question = next_stage_missing[0][1]
                            state["response"] = f"{stage_intro}\n\n{next_question}".strip() if stage_intro else next_question
                        else:
                            state["response"] = "Moving to the next stage."
                        return state

                    state["next_stage"] = "completed"
                    state["response"] = self._STAGE_INTRODUCTIONS.get("completed", "Congratulations! You've completed onboarding.")
                    return state

                # If they didn't explicitly confirm moving on, allow Q&A via the normal RAG+LLM path below.

            missing_before = self._missing_fields(
                current_stage,
                onboarding_facts,
                generated_question_bank=state.get("generated_question_bank"),
            )
            current_field_key, current_question = missing_before[0] if missing_before else (None, None)

            message_count = state.get("short_term_context", {}).get("message_count", 0)
            kickoff = str(state.get("user_input") or "").strip().lower().startswith("i just arrived")

            if kickoff:
                stage_names = {
                    "welcome": "Welcome",
                    "profile_setup": "Profile Setup", 
                    "learning_preferences": "Learning Preferences",
                    "first_steps": "First Steps"
                }
                
                completed_stages = []
                first_missing = None
                
                # If welcome isn't complete yet (name/role missing), don't attempt to evaluate later stages.
                welcome_missing = self._missing_fields(
                    "welcome",
                    onboarding_facts,
                    generated_question_bank=state.get("generated_question_bank"),
                )
                if welcome_missing:
                    first_missing = ("welcome", welcome_missing[0][0], welcome_missing[0][1])
                else:
                
                    for check_stage in ["welcome", "profile_setup", "learning_preferences", "first_steps"]:
                        if check_stage != "welcome":
                            try:
                                self._ensure_generated_question_bank(state, check_stage)
                            except Exception as e:
                                state["response"] = (
                                    "I can't generate the onboarding question bank right now because the web-search/question-generation "
                                    f"step failed: {type(e).__name__}: {e}\n\n"
                                    "Please check:\n"
                                    "- TAVILY_API_KEY is set\n"
                                    "- GOOGLE_API_KEY is set\n"
                                    "- GEMINI_MODEL is valid (e.g. models/gemini-2.0-flash)\n"
                                    "Then restart the app and click '🔄 New Session'."
                                )
                                state["next_stage"] = None
                                state["extracted_facts"] = {}
                                state["onboarding_facts"] = onboarding_facts
                                return state
                        missing = self._missing_fields(
                            check_stage,
                            onboarding_facts,
                            generated_question_bank=state.get("generated_question_bank"),
                        )
                        if not missing:
                            completed_stages.append(stage_names[check_stage])
                        elif not first_missing:
                            first_missing = (check_stage, missing[0][0], missing[0][1])
                
                response_parts = []
                
                if completed_stages:
                    response_parts.append(f"**Progress Summary:**\n✅ Completed: {', '.join(completed_stages)}")
                    response_parts.append("")
                
                if first_missing:
                    check_stage, field_key, question = first_missing
                    
                    if completed_stages:
                        response_parts.append(f"**Next Step:** {stage_names[check_stage]}")
                    
                    if check_stage != current_stage:
                        stage_intro = self._STAGE_INTRODUCTIONS.get(check_stage, "")
                        if stage_intro:
                            response_parts.append(stage_intro)
                    
                    if response_parts:
                        response_parts.append("")
                    response_parts.append(question)
                    
                    state["response"] = "\n".join(response_parts)
                    state["next_stage"] = check_stage if check_stage != current_stage else None
                else:
                    response_parts.append(self._STAGE_INTRODUCTIONS.get("completed", "Congratulations! You've completed onboarding."))
                    state["response"] = "\n".join(response_parts)
                    state["next_stage"] = "completed"
                
                state["extracted_facts"] = {}
                state["onboarding_facts"] = onboarding_facts
                return state

            if current_field_key and current_question:
                answer = str(state.get("user_input") or "").strip()
                if answer:
                    if current_stage == "welcome" and current_field_key == "name":
                        answer = self._deduplicate_name(answer)
                    namespaced_key = f"{current_stage}.{current_field_key}"
                    namespaced_extracted = {namespaced_key: answer}
                    state["extracted_facts"] = namespaced_extracted

                    known_name = None
                    if isinstance(namespaced_extracted.get("welcome.name"), str) and str(namespaced_extracted.get("welcome.name")).strip():
                        known_name = self._deduplicate_name(str(namespaced_extracted.get("welcome.name")).strip())
                    elif isinstance(onboarding_facts.get("welcome.name"), str) and str(onboarding_facts.get("welcome.name")).strip():
                        known_name = self._deduplicate_name(str(onboarding_facts.get("welcome.name")).strip())

                    onboarding_facts.update(namespaced_extracted)
                    state["onboarding_facts"] = onboarding_facts

                    remaining = self._missing_fields(
                        current_stage,
                        onboarding_facts,
                        generated_question_bank=state.get("generated_question_bank"),
                    )
                    if len(remaining) == 0:
                        # Current stage complete - move to next stage
                        next_stage = self._next_stage_for(current_stage)
                        if next_stage and next_stage != "completed":
                            state["next_stage"] = next_stage
                            try:
                                self._ensure_generated_question_bank(state, next_stage)
                            except Exception as e:
                                state["response"] = (
                                    "I can't generate role-based onboarding questions for the next stage because the web-search/question-generation "
                                    f"step failed: {type(e).__name__}: {e}\n\n"
                                    "Please check:\n"
                                    "- TAVILY_API_KEY is set\n"
                                    "- GOOGLE_API_KEY is set\n"
                                    "- GEMINI_MODEL is valid (e.g. models/gemini-2.0-flash)"
                                )
                                return state
                            # Get first question of next stage
                            next_stage_missing = self._missing_fields(
                                next_stage,
                                onboarding_facts,
                                generated_question_bank=state.get("generated_question_bank"),
                            )
                            if next_stage_missing:
                                next_question = next_stage_missing[0][1]
                                stage_intro = self._STAGE_INTRODUCTIONS.get(next_stage, "")
                                ack = f"Thanks, {known_name}!" if known_name and current_stage == "welcome" and current_field_key == "name" else "Got it!"
                                if stage_intro:
                                    state["response"] = f"{ack}\n\n{stage_intro}\n\n{next_question}"
                                else:
                                    state["response"] = f"{ack}\n\n{next_question}"
                            else:
                                state["response"] = "Got it! Moving to the next stage."
                        else:
                            # Onboarding complete
                            state["next_stage"] = "completed"
                            state["response"] = "Got it!\n\n" + self._STAGE_INTRODUCTIONS.get("completed", "Congratulations! You've completed onboarding.")
                    else:
                        state["next_stage"] = None
                        next_question = remaining[0][1]
                        ack = f"Thanks, {known_name}." if known_name and current_stage == "welcome" and current_field_key == "name" else "Got it."
                        state["response"] = f"{ack}\n\n{next_question}"

                    return state

            stage_prompts = {
                "welcome": """You are the friendly onboarding guide for TechVenture Solutions.

ABOUT TECHVENTURE SOLUTIONS:
TechVenture Solutions is a modern project management and team collaboration platform designed to help teams work smarter. Key features include:
- **Project & Task Management**: Create projects, assign tasks, set deadlines, and track progress
- **Team Collaboration**: Real-time chat, file sharing, and collaborative workspaces
- **Integrations**: Connect with Slack, Jira, Google Workspace, and 50+ other tools
- **Analytics & Reporting**: Track team performance, project health, and resource allocation
- **Automation**: Automate repetitive workflows and notifications

Our mission is to eliminate busywork so teams can focus on what matters most.

YOUR ROLE:
You're here to welcome newcomers, help them feel at home, and learn about them so we can personalize their experience. Share relevant company info naturally as you chat — don't just ask questions, have a real conversation!

When acknowledging their answers, share something relevant about TechVenture Solutions that connects to what they said.
""",
                "profile_setup": """You are helping the user build their profile at TechVenture Solutions.

WHY PROFILES MATTER:
- Teammates can find and collaborate with you easily
- Approvals and support requests get routed to the right people
- You'll receive relevant notifications and recommendations
- Your timezone helps schedule meetings and set working hours

COMPANY CULTURE:
At TechVenture Solutions, we believe in transparency and collaboration. Profiles are visible to teammates to foster connection. We support remote, hybrid, and office work arrangements across all timezones.

YOUR ROLE:
Guide them through profile setup while explaining how each piece of information helps them and their team. Make it feel valuable, not bureaucratic.
""",
                "learning_preferences": """You are learning how the user works best to customize their TechVenture Solutions experience.

WHAT WE CAN CUSTOMIZE:
- **Dashboard layout**: Focus on what matters most to you
- **Notification preferences**: Email, in-app, Slack — your choice, your frequency
- **Integrations**: Connect the tools you already use
- **Learning resources**: Docs, videos, hands-on tutorials, or live sessions

COMMON CHALLENGES WE SOLVE:
- Teams struggling with visibility across projects
- Too many meetings and status updates
- Scattered information across multiple tools
- Difficulty tracking who's working on what

YOUR ROLE:
Understand their workflow, challenges, and preferences. Share how TechVenture Solutions features can address their specific pain points. Make recommendations based on what they tell you.
""",
                "first_steps": """You are helping the user take their first real actions in TechVenture Solutions.

GETTING STARTED OPTIONS:
- **Create a project**: Set up your first project with tasks and milestones
- **Invite teammates**: Bring your team into TechVenture Solutions
- **Explore templates**: Use pre-built templates for common workflows
- **Set up integrations**: Connect Slack, calendar, or other tools
- **Take a quick tour**: 5-minute interactive walkthrough

SUPPORT RESOURCES:
- Help Center with searchable documentation
- Video tutorials (2-5 minutes each)
- Live chat support during business hours
- Community forum for tips and best practices

YOUR ROLE:
Help them take meaningful first steps. Offer guidance based on their role and goals. Celebrate their progress and make them feel confident using the platform.
""",
                "completed": """The user has completed onboarding — celebrate and support them!

WHAT'S NEXT:
- Explore advanced features like automation and custom workflows
- Join the TechVenture Solutions community for tips and networking
- Check out the weekly webinars on productivity and collaboration
- Reach out anytime — I'm here to help with questions big or small

ADVANCED FEATURES TO EXPLORE:
- Custom dashboards and reports
- Workflow automation rules
- Advanced permissions and team management
- API access for custom integrations

YOUR ROLE:
Congratulate them warmly! Offer ongoing support and suggest next steps based on their role and interests. Make them feel like part of the TechVenture Solutions community.
"""
            }
            
            context_section = ""
            if state.get("context_string"):
                context_section = f"\n\nRelevant Documentation:\n{state['context_string']}\n"
            
            memory_section = ""
            if state.get("long_term_memories"):
                memory_items = [f"- {m['key']}: {m['value']}" for m in state["long_term_memories"][:3]]
                memory_section = f"\n\nUser Preferences:\n" + "\n".join(memory_items) + "\n"
            
            system_prompt = f"""You are a warm, friendly onboarding assistant for TechVenture Solutions - a project management and collaboration platform.

Current Onboarding Stage: {current_stage}
{stage_prompts.get(current_stage, '')}

Your Approach:
- Be warm, welcoming, and genuinely interested in helping
- Ask ONE question at a time - keep it conversational, not overwhelming
- Always acknowledge what the user shares before moving forward
- Guide them naturally through the onboarding journey
- Use the documentation when answering specific questions
- Keep responses friendly and concise (2-4 sentences max)
- Show enthusiasm and encouragement
{context_section}{memory_section}

STEP-BY-STEP CONTROL:
- You must follow the onboarding step-by-step. its not foribiden to ask random questions.
- If there is a current question, the user input is the answer to that question.
- Extract the answer into `extracted_facts` using the key `{current_stage}.<field>`.
- Only produce a short acknowledgement/confirmation in `response` (do NOT ask the next question yourself; the system will add it).

CURRENT QUESTION FIELD: {current_field_key}
CURRENT QUESTION TEXT: {current_question}

Remember: You're here to guide and welcome users, making them feel comfortable and excited about getting started!

IMPORTANT OUTPUT FORMAT:
- Your user-facing message must be in a JSON control block at the end.
- Always end your message with a fenced code block in the following format:

```json
{{
  "response": "<what you want to say to the user>",
  "next_stage": "welcome" | "profile_setup" | "learning_preferences" | "first_steps" | "completed" | null,
  "extracted_facts": {{ "key": "value" }}
}}
```

Rules:
- Put ONLY the JSON in that block.
- Set `next_stage` to null. Stage progression is handled by the system.
- `extracted_facts` must include ONLY the answer to the CURRENT QUESTION FIELD (if one exists).
"""
            
            messages = [SystemMessage(content=system_prompt)]
            
            recent_messages = state.get("short_term_context", {}).get("recent_messages", [])
            for msg in recent_messages[-3:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=state["user_input"]))
            
            response = self.llm.invoke(messages)

            raw = response.content or ""
            parsed_response = None
            parsed_next_stage = None
            parsed_facts: Dict[str, Any] = {}

            matches = re.findall(r"```json\s*(\{[\s\S]*?\})\s*```", raw)
            if matches:
                try:
                    payload = json.loads(matches[-1])
                    parsed_response = payload.get("response")
                    parsed_next_stage = payload.get("next_stage")
                    parsed_facts = payload.get("extracted_facts") or {}
                except Exception:
                    parsed_response = None

            state["response"] = parsed_response if isinstance(parsed_response, str) and parsed_response.strip() else raw

            extracted = parsed_facts if isinstance(parsed_facts, dict) else {}
            namespaced_extracted: Dict[str, Any] = {}
            if current_field_key:
                key = f"{current_stage}.{current_field_key}"
                if key in extracted:
                    namespaced_extracted[key] = extracted.get(key)
                elif current_field_key in extracted:
                    namespaced_extracted[key] = extracted.get(current_field_key)
                else:
                    fallback_value = str(state.get("user_input") or "").strip()
                    if fallback_value:
                        namespaced_extracted[key] = fallback_value

            state["extracted_facts"] = namespaced_extracted

            known_name = None
            extracted_name = namespaced_extracted.get("welcome.name")
            if isinstance(extracted_name, str) and extracted_name.strip():
                known_name = self._deduplicate_name(extracted_name.strip())
            elif isinstance(onboarding_facts.get("welcome.name"), str) and str(onboarding_facts.get("welcome.name")).strip():
                known_name = self._deduplicate_name(str(onboarding_facts.get("welcome.name")).strip())

            if known_name and len(known_name) >= 2 and state.get("response"):
                resp = str(state["response"])
                # Fix doubled names in response (case-insensitive)
                pattern = re.compile(re.escape(known_name) + r"\s*" + re.escape(known_name), re.IGNORECASE)
                resp = pattern.sub(known_name, resp)
                state["response"] = resp

            onboarding_facts.update(namespaced_extracted)
            state["onboarding_facts"] = onboarding_facts

            guidance = ""
            if current_field_key:
                key = f"{current_stage}.{current_field_key}"
                if key in namespaced_extracted:
                    guidance = self._tailored_guidance(current_stage, current_field_key, namespaced_extracted.get(key))

            remaining = self._missing_fields(
                current_stage,
                onboarding_facts,
                generated_question_bank=state.get("generated_question_bank"),
            )
            if len(remaining) == 0:
                # Stage is complete - automatically move to next stage
                captured_new_required_info = bool(missing_before) and bool(namespaced_extracted)
                if captured_new_required_info:
                    # Just completed the last field for this stage
                    base = (state.get("response") or "").strip()
                    if guidance:
                        base = f"{base}\n\n{guidance}".strip() if base else guidance

                    # Stage complete -> enter Q&A mode instead of auto-advancing.
                    state["next_stage"] = None
                    qa_prompt = "Stage complete. Do you have any questions about this stage? I can answer using your uploaded docs. When you're ready, say 'move on' to continue."
                    state["response"] = f"{base}\n\n{qa_prompt}".strip() if base else qa_prompt

                    # Persist the Q&A pending stage so it survives reruns.
                    namespaced_extracted["qa.pending_stage"] = current_stage
                    state["extracted_facts"] = namespaced_extracted
                else:
                    # Stage was already complete. If the user is asking a question, allow the normal
                    # RAG+LLM path (below) to answer it instead of returning a canned message.
                    _text = str(state.get("user_input") or "").strip().lower()
                    _is_question = (
                        "?" in _text
                        or _text.startswith("what ")
                        or _text.startswith("why ")
                        or _text.startswith("how ")
                        or _text.startswith("when ")
                        or _text.startswith("where ")
                        or _text.startswith("who ")
                        or _text.startswith("can you ")
                        or _text.startswith("should i ")
                    )
                    if not _is_question:
                        state["response"] = "This stage is already complete. You can ask me questions about TechVenture Solutions, or I can help you with the next stage."
                        state["next_stage"] = None
                        logger.info("Stage complete message returned (input did not look like a question)")
                        return state
            else:
                state["next_stage"] = None

                next_question = remaining[0][1]
                base = (state.get("response") or "").strip()
                if guidance:
                    base = f"{base}\n\n{guidance}".strip() if base else guidance
                if base and next_question.strip().lower() in base.lower():
                    state["response"] = base
                else:
                    state["response"] = f"{base}\n\n{next_question}".strip() if base else next_question
            
            logger.info("Generated response successfully")
            
        except Exception as e:
            logger.exception("Error in generate_response")
            # If misconfigured LLM provider is the cause, give an actionable hint.
            google_key = str(getattr(settings, "GOOGLE_API_KEY", "") or "").strip()
            if not google_key:
                state["response"] = "AI responses are not configured (missing GOOGLE_API_KEY). Please set it and try again."
            else:
                state["response"] = "I apologize, but I encountered an error generating a response. Please try again."
            state["error"] = str(e)
            state["next_stage"] = None
            state["extracted_facts"] = {}
            state["onboarding_facts"] = state.get("onboarding_facts") or {}
        
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

            extracted_facts = state.get("extracted_facts") or {}
            if isinstance(extracted_facts, dict) and extracted_facts:
                for key, value in extracted_facts.items():
                    if key and value is not None:
                        ltm.save_memory(
                            user_id=state["user_id"],
                            memory_type="onboarding",
                            key=str(key),
                            value=value,
                            importance=4
                        )
            
            ltm.update_onboarding_progress(
                state["user_id"],
                state.get("next_stage") or state["current_stage"],
                f"conversation_{state['session_id'][:8]}"
            )

            facts = state.get("onboarding_facts") or {}
            role_value = facts.get("welcome.role")
            if role_value:
                bank = state.get("generated_question_bank")
                checklist = state.get("onboarding_checklist")
                research = state.get("role_research")

                if isinstance(bank, dict) and bank:
                    for stage_key, stage_questions in bank.items():
                        if not isinstance(stage_questions, list) or not stage_questions:
                            continue
                        ltm.save_memory(
                            user_id=state["user_id"],
                            memory_type="onboarding_generated",
                            key=self._generated_bank_cache_key(role_value, stage_key),
                            value=stage_questions,
                            importance=3,
                        )
                if isinstance(checklist, list) and checklist:
                    ltm.save_memory(
                        user_id=state["user_id"],
                        memory_type="onboarding_generated",
                        key=self._generated_checklist_cache_key(role_value),
                        value=checklist,
                        importance=3,
                    )
                if isinstance(research, dict) and research:
                    for stage_key, stage_research in research.items():
                        if not isinstance(stage_research, dict) or not stage_research:
                            continue
                        ltm.save_memory(
                            user_id=state["user_id"],
                            memory_type="onboarding_generated",
                            key=self._role_research_cache_key(role_value, stage_key),
                            value=stage_research,
                            importance=2,
                        )
            
            logger.info("Saved conversation to memory")
            
        except Exception as e:
            logger.error(f"Error in save_memory: {e}")
        
        return state
