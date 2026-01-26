from typing import Dict, Any
import json
import re
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

    _ROLE_STAGE_FIELDS: Dict[str, Dict[str, list[tuple[str, str]]]] = {
        "developer": {
            "profile_setup": [
                ("dev_stack", "Which programming language(s) or tech stack will you work with most here?"),
                ("dev_repo_access", "Which repos/projects do you need access to first (or which team are you joining)?"),
                ("dev_env", "What’s your preferred dev setup (IDE, OS, local vs. container/devbox)?")
            ],
            "learning_preferences": [
                ("dev_workflow", "How do you usually work: feature branches, trunk-based, or something else?"),
                ("dev_quality", "What matters most for you early on: tests/CI, code review flow, or local environment speed?"),
                ("dev_integrations", "Which tools should we integrate first for your workflow (e.g., GitHub, Jira, Slack)?")
            ],
            "first_steps": [
                ("dev_first_task", "Do you already have a first ticket/issue to start with? If yes, what is it about?"),
                ("dev_access_blockers", "Anything blocking you right now (accounts, permissions, VPN, SSO, repo access)?"),
                ("dev_help_area", "Where do you want help first: environment setup, permissions, or finding the right docs?"),
            ],
        },
        "pm": {
            "profile_setup": [
                ("pm_area", "What kind of work do you manage most (product, delivery, internal ops, client projects)?"),
                ("pm_reporting", "What reporting cadence do you need (weekly status, sprint reviews, exec dashboards)?"),
                ("pm_stakeholders", "Who are your main stakeholders (team, leadership, clients) so we can shape updates accordingly?")
            ],
            "learning_preferences": [
                ("pm_planning_style", "Do you plan work in sprints, kanban, or a hybrid approach?"),
                ("pm_pain", "What’s the biggest pain today: visibility, prioritization, dependencies, or stakeholder updates?"),
                ("pm_integrations", "Which tools should we integrate first (e.g., Jira, Slack, Google Workspace)?")
            ],
            "first_steps": [
                ("pm_first_project", "Do you want to set up your first project, or import an existing one?"),
                ("pm_team_invite", "Who should we invite first (team members or stakeholders)?"),
                ("pm_help_area", "Where do you want help first: project setup, reporting, or permissions?"),
            ],
        },
        "it_admin": {
            "profile_setup": [
                ("it_scope", "What are you responsible for here: user provisioning, integrations, security, or all of the above?"),
                ("it_sso", "Do you need SSO/SCIM (Okta/Azure AD/Google) enabled from day one?"),
                ("it_compliance", "Any compliance/security requirements we should align with (SOC2, ISO, audit logs, retention)?")
            ],
            "learning_preferences": [
                ("it_integrations", "Which integrations are highest priority (Slack, Jira, Google Workspace, email)?"),
                ("it_permissions", "How do you want permissions structured: least privilege by default, or flexible team-managed access?"),
                ("it_notifications", "Where should admin alerts go (email, Slack) and who should be notified?")
            ],
            "first_steps": [
                ("it_first_action", "What should we set up first: SSO, integrations, or a workspace permission baseline?"),
                ("it_users", "How many users are you onboarding initially, and do you need groups/teams pre-created?"),
                ("it_help_area", "Where do you want help first: SSO/SCIM, integrations, or permissions?"),
            ],
        },
        "general": {
            "profile_setup": [
                ("focus_area", "What will you use TechVenture for most: planning, execution, or coordination across teams?"),
            ],
            "learning_preferences": [
                ("preferred_learning", "How do you prefer to learn: quick tour, docs, or hands-on walkthrough?"),
            ],
            "first_steps": [
                ("first_setup", "What do you want to set up first: a project, inviting teammates, or integrations?"),
            ],
        },
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
            "Let's understand how you work best! This stage helps us tailor TechVenture to your "
            "workflow, recommend the right integrations, and set up notifications that work for you — "
            "not against you. The better we understand your needs, the more productive you'll be."
        ),
        "first_steps": (
            "🚀 **First Steps**\n\n"
            "Time to take action! In this stage, we'll make sure you have everything you need to hit "
            "the ground running — from account access to creating your first project. This is where "
            "onboarding becomes real and you start seeing TechVenture in action."
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

    @classmethod
    def _missing_fields(cls, stage: str, facts: Dict[str, Any]) -> list[tuple[str, str]]:
        stage = cls._normalize_stage_key(stage)
        missing: list[tuple[str, str]] = []

        fields: list[tuple[str, str]] = list(cls._STAGE_FIELDS.get(stage, []))

        role_value = facts.get("welcome.role")
        role_category = cls._role_category(role_value) if role_value else "general"

        if stage != "welcome":
            fields.extend(cls._ROLE_STAGE_FIELDS.get(role_category, {}).get(stage, []))

        for field_key, question in fields:
            namespaced = f"{stage}.{field_key}"
            if namespaced not in facts or facts.get(namespaced) in (None, ""):
                missing.append((field_key, question))
        return missing

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
            
            important_memories = ltm.get_important_memories(
                state["user_id"],
                min_importance=3
            )
            
            state["long_term_memories"] = important_memories

            onboarding_facts = self._facts_from_memories(important_memories)

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
            missing_before = self._missing_fields(current_stage, onboarding_facts)
            current_field_key, current_question = missing_before[0] if missing_before else (None, None)

            message_count = state.get("short_term_context", {}).get("message_count", 0)
            kickoff = str(state.get("user_input") or "").strip().lower().startswith("i just arrived")

            if kickoff:
                if current_question:
                    state["response"] = current_question
                else:
                    # All fields complete for this stage - provide a welcome with company info
                    state["response"] = (
                        "Welcome back! Great to see you again. I see we've already collected your basic info. "
                        "Feel free to ask me anything about TechVenture Solutions, or let me know if you'd like "
                        "to continue to the next stage of onboarding."
                    )
                state["next_stage"] = None
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

                    remaining = self._missing_fields(current_stage, onboarding_facts)
                    if len(remaining) == 0:
                        state["next_stage"] = None
                        state["response"] = "Got it."
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

When acknowledging their answers, share something relevant about TechVenture that connects to what they said.
""",
                "profile_setup": """You are helping the user build their profile at TechVenture Solutions.

WHY PROFILES MATTER:
- Teammates can find and collaborate with you easily
- Approvals and support requests get routed to the right people
- You'll receive relevant notifications and recommendations
- Your timezone helps schedule meetings and set working hours

COMPANY CULTURE:
At TechVenture, we believe in transparency and collaboration. Profiles are visible to teammates to foster connection. We support remote, hybrid, and office work arrangements across all timezones.

YOUR ROLE:
Guide them through profile setup while explaining how each piece of information helps them and their team. Make it feel valuable, not bureaucratic.
""",
                "learning_preferences": """You are learning how the user works best to customize their TechVenture experience.

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
Understand their workflow, challenges, and preferences. Share how TechVenture features can address their specific pain points. Make recommendations based on what they tell you.
""",
                "first_steps": """You are helping the user take their first real actions in TechVenture.

GETTING STARTED OPTIONS:
- **Create a project**: Set up your first project with tasks and milestones
- **Invite teammates**: Bring your team into TechVenture
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
- Join the TechVenture community for tips and networking
- Check out the weekly webinars on productivity and collaboration
- Reach out anytime — I'm here to help with questions big or small

ADVANCED FEATURES TO EXPLORE:
- Custom dashboards and reports
- Workflow automation rules
- Advanced permissions and team management
- API access for custom integrations

YOUR ROLE:
Congratulate them warmly! Offer ongoing support and suggest next steps based on their role and interests. Make them feel like part of the TechVenture community.
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
                import re as re_mod
                pattern = re_mod.compile(re_mod.escape(known_name) + r"\s*" + re_mod.escape(known_name), re_mod.IGNORECASE)
                resp = pattern.sub(known_name, resp)
                state["response"] = resp

            onboarding_facts.update(namespaced_extracted)
            state["onboarding_facts"] = onboarding_facts

            guidance = ""
            if current_field_key:
                key = f"{current_stage}.{current_field_key}"
                if key in namespaced_extracted:
                    guidance = self._tailored_guidance(current_stage, current_field_key, namespaced_extracted.get(key))

            remaining = self._missing_fields(current_stage, onboarding_facts)
            if len(remaining) == 0:
                # Only advance if this turn actually captured new info required for this stage.
                # This avoids auto-advancing due to previously persisted facts.
                captured_new_required_info = bool(missing_before) and bool(namespaced_extracted)
                if captured_new_required_info:
                    # Do NOT auto-advance stages here. The UI controls progression via a button.
                    state["next_stage"] = None
                else:
                    state["next_stage"] = None
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
            logger.error(f"Error in generate_response: {e}")
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
            
            logger.info("Saved conversation to memory")
            
        except Exception as e:
            logger.error(f"Error in save_memory: {e}")
        
        return state
