from typing import Dict, Any
import json
import re
import urllib.request
import urllib.error
import traceback
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
            ("name", "Welcome to your first day! What's your full name?"),
            ("role", "What role or position are you onboarding for? (e.g., IT Admin, Developer, Project Manager)"),
            ("department", "Which department are you joining?"),
            ("email_preference", "We'll set up your work email — what format would you prefer? (e.g., john.doe, jdoe, john.d)"),
            ("phone_number", "What's your phone number so we can reach you if needed?"),
            ("emergency_contact", "For safety purposes, could you share an emergency contact name and phone number?"),
            ("pronouns", "What are your preferred pronouns? (e.g., he/him, she/her, they/them)"),
            ("accessibility_needs", "Do you have any accessibility needs or accommodations we should know about? (Type 'none' if not applicable)"),
        ],
        "department_info": [],
        "key_responsibilities": [],
        "tools_systems": [],
        "training_needs": [],
        "completed": []
    }

    _STAGE_ORDER = ["welcome", "department_info", "key_responsibilities", "tools_systems", "training_needs", "completed"]

    _STAGE_QA_PROMPTS: Dict[str, str] = {
        "welcome": (
            "Before we move on — do you have any questions about TechVenture Solutions or the onboarding process? "
            "I can look up answers from our company documents. If you're all set, just say **'move on'** and we'll continue!"
        ),
        "department_info": (
            "That covers your department overview! Do you have any questions about the org structure, "
            "your team, or key stakeholders? I can search our company docs for you. "
            "Otherwise, say **'move on'** to proceed."
        ),
        "key_responsibilities": (
            "Great, your responsibilities and goals are mapped out! Any questions about your KPIs, "
            "decision-making scope, or initial tasks? I can look up answers from our knowledge base. "
            "When you're ready, say **'move on'** to continue."
        ),
        "tools_systems": (
            "Your tools and systems setup is covered! Do you have any questions about access credentials, "
            "software, hardware, or IT support? I'll check our company documents for you. "
            "Say **'move on'** when you're ready to continue."
        ),
        "training_needs": (
            "Awesome — your training plan is set! Do you have any questions about compliance modules, "
            "learning resources, or skill development? I can search our knowledge base for answers. "
            "Say **'move on'** when you're ready to wrap up."
        ),
    }

    _QA_FALLBACK_CONTACTS: Dict[str, str] = {
        "it": "the **IT Help Desk** (helpdesk@techventure.com)",
        "access": "the **IT Help Desk** (helpdesk@techventure.com)",
        "permission": "the **IT Help Desk** (helpdesk@techventure.com)",
        "security": "the **Security Team** (security@techventure.com)",
        "password": "the **IT Help Desk** (helpdesk@techventure.com)",
        "hr": "the **HR Department** (hr@techventure.com)",
        "leave": "the **HR Department** (hr@techventure.com)",
        "vacation": "the **HR Department** (hr@techventure.com)",
        "salary": "the **HR Department** (hr@techventure.com)",
        "benefit": "the **HR Department** (hr@techventure.com)",
        "payroll": "the **HR Department** (hr@techventure.com)",
        "contract": "the **HR Department** (hr@techventure.com)",
        "expense": "the **Finance Team** (finance@techventure.com)",
        "travel": "the **Finance Team** (finance@techventure.com)",
        "reimbursement": "the **Finance Team** (finance@techventure.com)",
        "billing": "the **Finance Team** (finance@techventure.com)",
        "manager": "your **direct manager**",
        "team": "your **direct manager**",
        "project": "your **project lead or direct manager**",
    }

    _QA_DEFAULT_FALLBACK = (
        "I wasn't able to find a specific answer in our company documents. "
        "For more details, I'd recommend reaching out to {contact}. "
        "They'll be happy to help!\n\n"
        "Do you have any other questions, or shall we **move on**?"
    )

    _QA_COMPLETED_FALLBACK = (
        "I wasn't able to find a specific answer in our company documents. "
        "For more details, I'd recommend reaching out to {contact}. "
        "They'll be happy to help!"
    )

    _QA_DEFAULT_CONTACT = "your **direct manager** or the **HR Department** (hr@techventure.com)"

    _STAGE_INTRODUCTIONS: Dict[str, str] = {
        "department_info": (
            "🏢 **Department Information**\n\n"
            "Let's get you familiar with your team and department! I'll share the org structure, "
            "introduce key stakeholders, and help you understand how your department fits into "
            "TechVenture Solutions. We'll also schedule some intro meetings for you."
        ),
        "key_responsibilities": (
            "🎯 **Key Responsibilities**\n\n"
            "Now let's outline your role in detail! We'll cover your specific duties, KPIs, "
            "first-week and first-month goals, decision-making scope, and success metrics. "
            "I'll also assign some initial tasks to get you started."
        ),
        "tools_systems": (
            "🛠️ **Tools & Systems**\n\n"
            "Time to get your tech stack set up! We'll walk through IT access, software installs, "
            "hardware checklist, and make sure you can log into everything you need. "
            "I'll guide you through tutorials and troubleshoot any issues."
        ),
        "training_needs": (
            "📚 **Training Needs**\n\n"
            "Let's build your personalized learning path! We'll cover mandatory compliance training, "
            "role-specific modules, and identify any skill gaps. I'll set up reminders and "
            "schedule a 30-day check-in to make sure everything is on track."
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

    @staticmethod
    def _is_meta_question(user_input: str) -> bool:
        """Return True if the user is asking ABOUT the current onboarding question
        rather than answering it (e.g. 'why does this matter?', 'what is the
        purpose of this question?')."""
        text = user_input.strip().lower()
        meta_patterns = [
            "why this question",
            "why do you ask",
            "why are you asking",
            "why does this matter",
            "why does it matter",
            "why is this important",
            "why is that important",
            "what is the purpose",
            "what's the purpose",
            "whats the purpose",
            "purpose of this question",
            "purpose of that question",
            "why do you need",
            "why do you want to know",
            "why do i need to answer",
            "what does this have to do",
            "why is this relevant",
            "why is this needed",
            "why should i answer",
            "what for",
            "why is this asked",
            "why ask this",
            "why ask that",
            "can you explain why",
            "explain why you ask",
            "what's the point",
            "whats the point",
            "why does this question matter",
            "why this matters",
            "how is this relevant",
            "is this really necessary",
            "do i have to answer",
            "why do you need this",
            "why do you need that",
        ]
        return any(p in text for p in meta_patterns)

    def _handle_meta_question(
        self,
        state: OnboardingAgentState,
        current_stage: str,
        current_question: str,
        onboarding_facts: dict,
    ) -> OnboardingAgentState:
        """Use the LLM to explain why the current onboarding question matters,
        then re-ask the same question so the user can still answer it."""
        user_input = str(state.get("user_input") or "").strip()
        logger.info(f"Meta-question detected – explaining: {user_input[:120]}")

        system_prompt = (
            "You are a friendly onboarding assistant for TechVenture Solutions.\n"
            "The newcomer was asked the following onboarding question:\n\n"
            f"  \"{current_question}\"\n\n"
            "Instead of answering, they want to know WHY this question is being asked "
            "or what purpose it serves.\n\n"
            "Explain briefly (2-4 sentences) why this question matters for their "
            "onboarding experience, how the information will be used, and why it "
            "benefits them. Be warm and reassuring — never make them feel forced.\n\n"
            "After your explanation, politely re-ask the same question so they can "
            "answer it when ready."
        )

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input),
            ]
            llm_response = self.llm.invoke(messages)
            answer = (llm_response.content or "").strip()
            if not answer:
                raise ValueError("Empty LLM response")
        except Exception as e:
            logger.error(f"LLM failed explaining meta-question: {e}")
            answer = (
                f"Great question! We ask this to make your onboarding experience as "
                f"smooth and personalised as possible. The information helps us tailor "
                f"the process to your needs.\n\n{current_question}"
            )

        state["response"] = answer
        state["next_stage"] = None
        state["extracted_facts"] = {}
        state["onboarding_facts"] = onboarding_facts
        return state

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

        stage_guidance = {
            "department_info": (
                "This stage is about TELLING the newcomer about their department. "
                "Generate questions that CHECK UNDERSTANDING or ask about PREFERENCES — "
                "e.g., 'Does that make sense?', 'Would you like me to schedule a 1:1 with your manager?', "
                "'Is there anyone specific you'd like to meet first?'"
            ),
            "key_responsibilities": (
                "This stage is about EXPLAINING the newcomer's responsibilities. "
                "Generate questions that CONFIRM ALIGNMENT or ask about INTEREST — "
                "e.g., 'Does this align with what you expected?', 'Which area are you most excited about?', "
                "'Would you like more detail on any of these responsibilities?'"
            ),
            "tools_systems": (
                "This stage is about WALKING the newcomer through IT setup. "
                "Generate questions that CHECK PROGRESS or ask about ISSUES — "
                "e.g., 'Were you able to log in?', 'Is everything working?', "
                "'Do you need help with any setup steps?'"
            ),
            "training_needs": (
                "This stage is about PRESENTING the training plan. "
                "Generate questions that ask about LEARNING PREFERENCES — "
                "e.g., 'Do you prefer videos or documentation?', 'Any specific skills you want to develop?', "
                "'Would you like reminders for training deadlines?'"
            ),
        }

        stage_hint = stage_guidance.get(stage, "Generate preference or confirmation questions.")

        prompt = f"""You are creating a role-specific onboarding guide for a new hire's FIRST DAY.

ROLE: {role}
STAGE: {stage}

IMPORTANT CONTEXT: The newcomer is brand new — they don't know anything about the company yet.
Your job is to generate content that GUIDES and INFORMS them, NOT quiz them on things they can't know.

{stage_hint}

Use the following web research snippets as background:
{research_block}

Return ONLY valid JSON with this schema:
{{
  "onboarding_checklist": ["..."],
  "questions": [{{"field": "q1", "question": "..."}}]
}}

Rules:
- Provide 5-10 checklist items relevant to the role and stage.
- Provide 3-5 questions ONLY for the given STAGE.
- Questions must be PREFERENCE, CONFIRMATION, or FEEDBACK questions — things the newcomer CAN answer.
- NEVER ask the newcomer to explain company structure, processes, or tools they haven't learned yet.
- Good: "Does that make sense?", "Would you like to know more about X?", "Any questions so far?"
- Bad: "Can you describe the department structure?", "What tools does your team use?"
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
                stage_search_focus = {
                    "department_info": f"{role} onboarding department structure team introduction first day",
                    "key_responsibilities": f"{role} job responsibilities KPIs first week goals onboarding",
                    "tools_systems": f"{role} IT setup tools software access onboarding first day",
                    "training_needs": f"{role} onboarding training plan compliance learning path",
                }
                search_query = stage_search_focus.get(stage, f"{role} onboarding {stage}")
                research_results = self._tavily_search(search_query, max_results=6)
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
                return "Nice — I'll tailor the onboarding toward developer workflows, tools, and technical setup."
            if any(k in low for k in ["pm", "project manager", "product", "scrum"]):
                return "Great — I'll focus on planning tools, stakeholder introductions, and reporting workflows."
            if any(k in low for k in ["it", "admin", "administrator"]):
                return "Perfect — I'll emphasize infrastructure access, admin tools, and security policies."

        if stage == "welcome" and field_key == "department":
            return f"Got it — {text}! I'll make sure the department-specific info is ready for you in the next stage."

        if stage == "welcome" and field_key == "accessibility_needs":
            if low not in ("none", "no", "n/a", "na", "nothing"):
                return "Thank you for sharing — we'll make sure your accommodations are in place before your first day."

        if stage == "department_info" and field_key == "team_familiarity":
            if any(k in low for k in ["no", "not", "don't", "dont", "new"]):
                return "No worries — we'll make sure you get properly introduced to everyone on your team."

        if stage == "key_responsibilities" and field_key == "alignment":
            if any(k in low for k in ["no", "not", "different", "unclear"]):
                return "Thanks for flagging that — I'd recommend discussing this with your manager to clarify expectations."

        if stage == "tools_systems" and field_key == "access_issues":
            if any(k in low for k in ["missing", "no", "not", "can't", "cant", "don\u2019t", "dont", "blocked"]):
                return "Thanks — we should unblock access first. I can help you list exactly what to request and escalate to IT if needed."

        if stage == "training_needs" and field_key == "learning_style":
            if "hands" in low or "walk" in low:
                return "Great — I'll give you short step-by-step walkthroughs you can follow immediately."
            if "video" in low:
                return "Great — I'll keep guidance in short, digestible chunks and point you to relevant video materials."
            if "doc" in low:
                return "Great — I'll keep answers structured and reference documentation sections when possible."

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
                for stage_key in ["department_info", "key_responsibilities", "tools_systems", "training_needs"]:
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

    def _handle_document_search(
        self,
        state: OnboardingAgentState,
        onboarding_facts: dict,
    ) -> OnboardingAgentState:
        """
        Handle document search queries after onboarding is completed.
        
        Args:
            state: Current agent state
            onboarding_facts: User's onboarding facts
            
        Returns:
            Updated state with response
        """
        logger.info("Handling document search (post-onboarding)")
        return self._handle_qa_question(state, "completed", onboarding_facts)
    
    # ------------------------------------------------------------------
    # Q&A helper: answer from RAG docs with a smart fallback
    # ------------------------------------------------------------------
    def _handle_qa_question(
        self,
        state: OnboardingAgentState,
        current_stage: str,
        onboarding_facts: dict,
    ) -> OnboardingAgentState:
        """Answer a user question during the post-stage Q&A pause.

        1. Retrieve documents from the RAG knowledge base.
        2. If high-relevance docs are found, use the LLM to synthesise an
           answer grounded in those documents.
        3. If no relevant docs are found (or scores are too low), return a
           friendly fallback that tells the user *who* to contact for help.
        """
        user_question = str(state.get("user_input") or "").strip()
        logger.info(f"Q&A mode – answering question: {user_question[:120]}")

        # --- 1. Retrieve from RAG ---
        MIN_RELEVANCE_SCORE = 0.05
        try:
            rag_result = self.rag.retrieve(
                query=user_question,
                current_stage=current_stage,
                top_k=20,
                use_reranking=False,
            )
            docs = rag_result.get("documents") or []
            logger.info(f"Retrieved {len(docs)} documents from RAG")
            
            # Prioritize internal rules documents
            internal_rules_docs = [
                d for d in docs
                if d.metadata.get("origin") == "internal_rules"
            ]
            other_docs = [
                d for d in docs
                if d.metadata.get("origin") != "internal_rules"
            ]
            
            logger.info(f"Found {len(internal_rules_docs)} internal rules docs and {len(other_docs)} other docs")
            
            # Keep only docs above the relevance threshold, prioritizing internal rules
            relevant_docs = [
                d for d in internal_rules_docs
                if d.metadata.get("score", 0.0) >= MIN_RELEVANCE_SCORE
            ]
            logger.info(f"Found {len(relevant_docs)} internal rules docs above threshold {MIN_RELEVANCE_SCORE}")
            
            # If no internal rules docs found, try keyword matching on internal rules
            if not relevant_docs:
                logger.info("No internal rules docs above threshold, trying keyword matching...")
                question_lower = user_question.lower()
                for doc in internal_rules_docs:
                    source = str(doc.metadata.get("source", "")).lower()
                    content = doc.page_content.lower()
                    
                    # Check if document source or content contains keywords from the question
                    keywords = question_lower.split()
                    matching_keywords = sum(1 for kw in keywords if len(kw) > 3 and kw in source)
                    
                    if matching_keywords >= 1 or any(kw in content for kw in ["administrator", "responsibilities", "admin", "kpi"]):
                        relevant_docs.append(doc)
                        logger.info(f"Keyword match found in {source}")
                        if len(relevant_docs) >= 3:
                            break
        except Exception as e:
            logger.error(f"RAG retrieval failed in Q&A mode: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            relevant_docs = []

        # --- 2. If we have relevant docs, ask the LLM to answer ---
        if relevant_docs:
            context_str = self.rag.get_context_string(relevant_docs)
            
            # Different prompts for onboarding vs post-onboarding
            if current_stage == "completed":
                qa_system_prompt = (
                    "You are a helpful assistant for TechVenture Solutions.\n"
                    "Answer the user's question using ONLY the company documents below.\n"
                    "Be concise (3-5 sentences). If the documents don't fully cover the question, "
                    "say so honestly and suggest who to contact.\n\n"
                    f"--- Company Documents ---\n{context_str}\n---"
                )
            else:
                qa_system_prompt = (
                    "You are a helpful onboarding assistant for TechVenture Solutions.\n"
                    "The newcomer has a question. Answer it using ONLY the company documents below.\n"
                    "Be concise (3-5 sentences). If the documents don't fully cover the question, "
                    "say so honestly and suggest who to contact.\n"
                    "After your answer, remind the user they can ask more questions or say "
                    "**'move on'** to continue onboarding.\n\n"
                    f"--- Company Documents ---\n{context_str}\n---"
                )
            try:
                messages = [
                    SystemMessage(content=qa_system_prompt),
                    HumanMessage(content=user_question),
                ]
                llm_response = self.llm.invoke(messages)
                answer = (llm_response.content or "").strip()
                if not answer:
                    raise ValueError("Empty LLM response")
            except Exception as e:
                logger.error(f"LLM failed in Q&A mode: {e}")
                answer = None

            if answer:
                state["response"] = answer
                state["next_stage"] = None
                state["extracted_facts"] = {}
                state["onboarding_facts"] = onboarding_facts
                # Expose sources so the UI can show them with clickable links
                sources = []
                for doc in relevant_docs:
                    # Strip YAML frontmatter from preview
                    content = doc.page_content
                    if content.startswith("doc_id:") or content.startswith("---"):
                        # Find where actual content starts (after metadata lines)
                        lines = content.split("\n")
                        content_start = 0
                        for idx, line in enumerate(lines):
                            # Skip metadata lines (key: value format or empty)
                            stripped = line.strip()
                            if stripped and not ":" in stripped[:30]:
                                content_start = idx
                                break
                        content = "\n".join(lines[content_start:]).strip()
                    preview_text = content[:150] + "..." if len(content) > 150 else content
                    
                    source_info = {
                        "source": doc.metadata.get("source", "unknown"),
                        "category": doc.metadata.get("category", "general"),
                        "score": doc.metadata.get("score", 0.0),
                        "preview": preview_text,
                        "file_name": doc.metadata.get("file_name", ""),
                        "upload_id": doc.metadata.get("upload_id", ""),
                    }
                    
                    # Add document link for clickable access
                    file_path = doc.metadata.get("file_path", "")
                    if file_path:
                        source_info["document_link"] = file_path
                    elif doc.metadata.get("source"):
                        # Construct link from source name
                        source_name = str(doc.metadata.get("source", "")).replace(" ", "_")
                        source_info["document_link"] = f"internal_rules/{source_name}"
                    
                    sources.append(source_info)
                state["sources"] = sources
                return state

        # --- 3. Fallback: no relevant docs found ---
        contact = self._QA_DEFAULT_CONTACT
        question_lower = user_question.lower()
        for keyword, dept in self._QA_FALLBACK_CONTACTS.items():
            if keyword in question_lower:
                contact = dept
                break

        # Use different fallback messages for onboarding vs post-onboarding
        if current_stage == "completed":
            fallback_template = self._QA_COMPLETED_FALLBACK
        else:
            fallback_template = self._QA_DEFAULT_FALLBACK
        
        state["response"] = fallback_template.format(contact=contact)
        state["next_stage"] = None
        state["extracted_facts"] = {}
        state["onboarding_facts"] = onboarding_facts
        state["sources"] = []
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
                    "preview": doc.page_content[:150] + "...",
                    "file_name": doc.metadata.get("file_name", ""),
                    "upload_id": doc.metadata.get("upload_id", ""),
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

            # --- Post-onboarding document search mode ---
            if current_stage == "completed":
                return self._handle_document_search(state, onboarding_facts)

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
                    "no questions",
                    "no, let's move on",
                    "no lets move on",
                    "nope",
                    "i'm good",
                    "im good",
                    "all good",
                    "no thanks",
                ]
            ) or (qa_pending_stage and user_low.strip() in ("no", "no."))
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

                # User is asking a question in Q&A mode — answer from RAG docs with fallback.
                return self._handle_qa_question(state, current_stage, onboarding_facts)

            # If qa_pending_stage is set for a DIFFERENT stage, user manually went back.
            # Show the QA prompt for the revisited stage.
            if qa_pending_stage and qa_pending_stage != current_stage:
                onboarding_facts["qa.pending_stage"] = current_stage
                state["onboarding_facts"] = onboarding_facts
                state["extracted_facts"] = {"qa.pending_stage": current_stage}
                
                qa_prompt = self._STAGE_QA_PROMPTS.get(
                    current_stage,
                    "Do you have any questions about this stage? I can look up answers from our company documents. When you're ready, say **'move on'** to continue."
                )
                state["response"] = qa_prompt
                state["next_stage"] = None
                return state

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
                    "welcome": "Welcome & Profile Setup",
                    "department_info": "Department Information", 
                    "key_responsibilities": "Key Responsibilities",
                    "tools_systems": "Tools & Systems",
                    "training_needs": "Training Needs"
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
                
                    for check_stage in ["welcome", "department_info", "key_responsibilities", "tools_systems", "training_needs"]:
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

                # --- Meta-question detection ---
                # If the user is asking ABOUT the current question (why it matters,
                # what its purpose is, etc.) instead of answering it, explain and
                # re-ask the same question without saving anything.
                if answer and self._is_meta_question(answer):
                    return self._handle_meta_question(
                        state, current_stage, current_question, onboarding_facts
                    )

                if answer:
                    if current_stage == "welcome" and current_field_key == "name":
                        answer = self._deduplicate_name(answer)
                    namespaced_key = f"{current_stage}.{current_field_key}"
                    namespaced_extracted = {namespaced_key: answer}
                    # Store the question text so the PDF summary can show it
                    # instead of raw field keys like "Q1", "Q2", etc.
                    qlabel_key = f"{current_stage}._qlabel.{current_field_key}"
                    namespaced_extracted[qlabel_key] = current_question
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
                        # Stage complete -> enter Q&A mode instead of auto-advancing.
                        ack = f"Thanks, {known_name}!" if known_name and current_stage == "welcome" and current_field_key == "name" else "Got it!"
                        qa_prompt = self._STAGE_QA_PROMPTS.get(
                            current_stage,
                            "Do you have any questions about this stage? I can look up answers from our company documents. When you're ready, say **'move on'** to continue."
                        )
                        state["response"] = f"{ack}\n\n{qa_prompt}"
                        state["next_stage"] = None
                        namespaced_extracted["qa.pending_stage"] = current_stage
                        state["extracted_facts"] = namespaced_extracted
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
It's the newcomer's first day! Welcome them warmly and collect the general information HR needs: full name, preferred name/nickname, the role they're onboarding for, department, their preferred work email format (e.g., john.doe@techventure.com), phone number, emergency contact, pronouns, and accessibility needs.

These are all things the newcomer already knows about themselves. Do NOT ask for things the company assigns (like employee ID, start date, or system credentials — those come later).

Keep it conversational and warm. When acknowledging their answers, share something relevant about TechVenture Solutions that connects to what they said.
""",
                "department_info": """You are GUIDING the newcomer through their department at TechVenture Solutions. This is their first day — they don't know the answers yet. YOUR job is to TELL THEM, not ask them.

YOUR APPROACH:
- PRESENT information about their department, don't quiz them on it
- EXPLAIN the org structure, who their manager is, who their teammates are
- DESCRIBE how the department fits into the company
- INTRODUCE key people they'll work with and what each person does
- OFFER to schedule intro meetings (1:1 with manager, team intro call)

After sharing each piece of info, ask a simple confirmation like "Does that make sense?" or "Any questions about that?" — NOT questions they couldn't possibly answer yet.

The only questions you should ask are about their PREFERENCES or FEELINGS:
- "Would you like me to schedule a 1:1 with your manager this week?"
- "Is there anyone specific you'd like to meet first?"
- "How are you feeling about the team so far?"

YOUR ROLE:
Be their friendly guide showing them around. Think of it like a tour — you're the one with the knowledge, they're the one learning. Make them feel welcomed into the team.
""",
                "key_responsibilities": """You are EXPLAINING the newcomer's role and responsibilities at TechVenture Solutions. They're new — walk them through what their job involves, don't expect them to already know.

YOUR APPROACH:
- TELL them what their day-to-day duties will look like
- EXPLAIN the KPIs and how success is measured in this role
- SHARE first-week priorities and quick wins they can aim for
- OUTLINE first-month goals and milestones
- CLARIFY what they can decide on their own vs. what needs approval

After presenting responsibilities, ask simple check-in questions:
- "Does this align with what you expected for the role?"
- "Any of these areas you'd like me to explain in more detail?"
- "What are you most excited to work on?"

Do NOT ask them to describe their own responsibilities — they don't know them yet. YOU are the one informing THEM.

YOUR ROLE:
Make the role feel clear and exciting, not overwhelming. Connect duties to the bigger picture. Assign a starter task with resources to get them contributing early.
""",
                "tools_systems": """You are WALKING the newcomer through their IT and tools setup at TechVenture Solutions. Guide them step by step — don't ask them what tools they need, TELL them what's being set up.

YOUR APPROACH:
- INFORM them about their email account, SSO credentials, and password policies
- WALK them through software they need to install (email client, Slack, VPN, IDE if applicable)
- PROVIDE their hardware checklist (laptop, monitors, peripherals)
- GUIDE them through logging into each core tool and verifying access
- OFFER quick tutorials on the most-used platforms

If something isn't working, help troubleshoot. Escalate to IT Help Desk (helpdesk@techventure.com) if needed.

The only questions to ask are practical ones:
- "Were you able to log in successfully?"
- "Is everything working on your end?"
- "Do you need help with any of the setup steps?"

YOUR ROLE:
Be their IT buddy. Walk them through setup step by step. Make tech setup feel manageable, not frustrating. Verify each tool works before moving on.
""",
                "training_needs": """You are PRESENTING the newcomer's training plan at TechVenture Solutions. Tell them what training they need to complete — don't ask them to design their own plan.

YOUR APPROACH:
- INFORM them about mandatory compliance training (security, data privacy, code of conduct)
- PRESENT role-specific training modules tailored to their position
- SHARE available learning resources (internal wiki, LMS courses, mentorship programs)
- EXPLAIN the training timeline and deadlines
- OFFER to help them get started with the first module

After presenting the plan, ask preference-based questions:
- "Do you prefer learning through videos, documentation, or hands-on exercises?"
- "Are there any specific skills you'd like to develop further?"
- "Would you like me to set up reminders for your training deadlines?"

Do NOT ask them what training they think they need — they're new and don't know yet. YOU present the plan, THEY give feedback on preferences.

YOUR ROLE:
Make training feel like an investment in their growth, not a checkbox exercise. Present a clear 30-day learning plan and offer to schedule a check-in.
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
  "next_stage": "welcome" | "department_info" | "key_responsibilities" | "tools_systems" | "training_needs" | "completed" | null,
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

            # Store the question text so the PDF summary can show it
            if current_field_key and current_question and namespaced_extracted:
                qlabel_key = f"{current_stage}._qlabel.{current_field_key}"
                namespaced_extracted[qlabel_key] = current_question
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
                    qa_prompt = self._STAGE_QA_PROMPTS.get(
                        current_stage,
                        "Do you have any questions about this stage? I can look up answers from our company documents. When you're ready, say **'move on'** to continue."
                    )
                    state["response"] = f"{base}\n\n{qa_prompt}".strip() if base else qa_prompt

                    # Persist the Q&A pending stage so it survives reruns.
                    namespaced_extracted["qa.pending_stage"] = current_stage
                    state["extracted_facts"] = namespaced_extracted
                else:
                    # Stage was already complete. If the user is asking a question, answer
                    # it from RAG docs instead of returning a canned message.
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
                        or _text.startswith("tell me ")
                        or _text.startswith("explain ")
                        or _text.startswith("describe ")
                        or _text.startswith("do we ")
                        or _text.startswith("do i ")
                        or _text.startswith("is there ")
                        or _text.startswith("are there ")
                        or "policy" in _text
                        or "procedure" in _text
                        or "rule" in _text
                        or "guideline" in _text
                        or "about " in _text
                        or "work from home" in _text
                        or "remote work" in _text
                    )
                    if _is_question:
                        return self._handle_qa_question(state, current_stage, onboarding_facts)
                    else:
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

    def _generate_completion_summary(self, onboarding_facts: dict) -> str:
        """
        Generate a user-friendly summary of completed onboarding.
        
        Args:
            onboarding_facts: Dictionary of collected onboarding facts
            
        Returns:
            Formatted summary string
        """
        user_name = onboarding_facts.get('welcome.name', 'Team Member')
        user_role = onboarding_facts.get('welcome.role', 'N/A')
        user_department = onboarding_facts.get('welcome.department', 'N/A')
        
        summary_parts = [
            f"## 🎉 Welcome to TechVenture Solutions, {user_name}!",
            "",
            "Your onboarding is now complete. Here's what we covered:",
            "",
            "### Your Profile",
            f"- **Name:** {user_name}",
            f"- **Role:** {user_role}",
            f"- **Department:** {user_department}",
            "",
            "### Onboarding Stages Completed",
            "✅ **Welcome & Profile Setup** — Your personal and contact information",
            "✅ **Department Information** — Team structure and key contacts",
            "✅ **Key Responsibilities** — Your role duties and success metrics",
            "✅ **Tools & Systems** — IT setup and software access",
            "✅ **Training Needs** — Learning paths and compliance training",
            "",
            "### What's Next?",
            "You're now fully set up and ready to contribute! Remember:",
            "- Check your email for important documents and access credentials",
            "- Reach out to your manager for any questions",
            "- Use the search feature below to find company policies and procedures",
            "- Schedule your 30-day check-in with HR",
            "",
            "**Questions?** I'm here to help! Search for any company policies, procedures, or internal rules using the search box below.",
        ]
        
        return "\n".join(summary_parts)
