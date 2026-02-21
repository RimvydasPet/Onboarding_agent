import streamlit as st
from pathlib import Path
from typing import List, Dict, Any
import uuid
import re
from io import BytesIO
import logging
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime
from datetime import timedelta
from sqlalchemy.orm import Session
from backend.database.models import UserDB, OnboardingProfileDB

logger = logging.getLogger(__name__)


class AdminUtils:
    """Utility functions for admin operations."""

    MOCK_USER_PASSWORD_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKxGhu6P4fBf6A7x9S6XrM4u3Q8m2fQ8hL9QK"

    @staticmethod
    def seed_mock_onboarding_users(db: Session) -> Dict[str, int]:
        """Create/update 5 mock users with full, half, and started onboarding states."""
        now = datetime.utcnow()
        internal_rules_dir = Path(__file__).resolve().parents[3] / "Internal rules"

        code_of_conduct_uri = (internal_rules_dir / "Employee Code of Conduct.md").resolve().as_uri()
        data_policy_uri = (internal_rules_dir / "Data Classification and Handling Standard.md").resolve().as_uri()
        access_standard_uri = (internal_rules_dir / "Access Request and Provisioning Standard.md").resolve().as_uri()
        endpoint_security_uri = (internal_rules_dir / "Endpoint Security Baseline.md").resolve().as_uri()
        it_credentials_uri = (internal_rules_dir / "IT Onboarding Credentials Guide.md").resolve().as_uri()

        mock_users = [
            {
                "email": "mock.full.1@company.test",
                "full_name": "Ava Johnson",
                "role": "user",
                "current_stage": "completed",
                "completed_steps": [
                    "welcome",
                    "department_info",
                    "key_responsibilities",
                    "tools_systems",
                    "training_needs",
                ],
                "facts": {
                    "welcome.name": "Ava Johnson",
                    "welcome.role": "Software Engineer",
                    "welcome.department": "Engineering",
                    "welcome.resources": f"Read document: Employee Code of Conduct {code_of_conduct_uri}",
                    "department_info.team_structure": "Platform team of 8 engineers.",
                    "department_info.references": f"Procedure: Access request standard {access_standard_uri}",
                    "key_responsibilities.primary_focus": "Backend API development.",
                    "key_responsibilities.references": "Guideline: API standards handbook",
                    "tools_systems.main_tools": "GitHub, Jira, Slack, VS Code.",
                    "tools_systems.references": f"Tool guide: Endpoint security baseline {endpoint_security_uri}",
                    "training_needs.priority_area": "Internal architecture onboarding.",
                    "training_needs.references": "Training document: Security Awareness Handbook",
                },
                "days_ago": 9,
            },
            {
                "email": "mock.full.2@company.test",
                "full_name": "Liam Carter",
                "role": "user",
                "current_stage": "completed",
                "completed_steps": [
                    "welcome",
                    "department_info",
                    "key_responsibilities",
                    "tools_systems",
                    "training_needs",
                ],
                "facts": {
                    "welcome.name": "Liam Carter",
                    "welcome.role": "Data Analyst",
                    "welcome.department": "Analytics",
                    "welcome.resources": "Policy: Data Access Policy",
                    "department_info.team_structure": "BI team with analysts and data engineers.",
                    "department_info.references": f"Document: Data classification standard {data_policy_uri}",
                    "key_responsibilities.primary_focus": "KPI dashboarding and reporting.",
                    "tools_systems.main_tools": "SQL, Power BI, Python.",
                    "tools_systems.references": "Procedure: BI dashboard release checklist",
                    "training_needs.priority_area": "Data governance policies.",
                    "training_needs.references": f"Guideline: Data handling standard {data_policy_uri}",
                },
                "days_ago": 7,
            },
            {
                "email": "mock.half.1@company.test",
                "full_name": "Noah Rivera",
                "role": "user",
                "current_stage": "key_responsibilities",
                "completed_steps": ["welcome", "department_info"],
                "facts": {
                    "welcome.name": "Noah Rivera",
                    "welcome.role": "QA Engineer",
                    "welcome.department": "Engineering",
                    "welcome.resources": "Read rule: QA release gates",
                    "department_info.team_structure": "QA pod supporting 3 product squads.",
                    "department_info.references": f"Document: Acceptable use policy {code_of_conduct_uri}",
                },
                "days_ago": 3,
            },
            {
                "email": "mock.half.2@company.test",
                "full_name": "Mia Patel",
                "role": "user",
                "current_stage": "tools_systems",
                "completed_steps": ["welcome", "department_info", "key_responsibilities"],
                "facts": {
                    "welcome.name": "Mia Patel",
                    "welcome.role": "Project Manager",
                    "welcome.department": "Operations",
                    "welcome.resources": "Policy: Project governance handbook",
                    "department_info.team_structure": "PMO team with cross-functional leads.",
                    "key_responsibilities.primary_focus": "Sprint planning and delivery tracking.",
                    "key_responsibilities.references": f"Procedure: Access request standard {access_standard_uri}",
                },
                "days_ago": 2,
            },
            {
                "email": "mock.started.1@company.test",
                "full_name": "Ethan Brooks",
                "role": "user",
                "current_stage": "welcome",
                "completed_steps": [],
                "facts": {
                    "welcome.name": "Ethan Brooks",
                    "welcome.role": "IT Administrator",
                    "welcome.department": "IT",
                    "welcome.resources": f"Document: IT onboarding credentials guide {it_credentials_uri}",
                },
                "days_ago": 1,
            },
        ]

        created = 0
        updated = 0

        for item in mock_users:
            user = db.query(UserDB).filter(UserDB.email == item["email"]).first()
            if not user:
                user = UserDB(
                    email=item["email"],
                    full_name=item["full_name"],
                    hashed_password=AdminUtils.MOCK_USER_PASSWORD_HASH,
                    is_active=True,
                    role=item["role"],
                    created_at=now - timedelta(days=item["days_ago"]),
                )
                db.add(user)
                db.flush()
                created += 1
            else:
                user.full_name = item["full_name"]
                user.role = item["role"]
                updated += 1

            profile = db.query(OnboardingProfileDB).filter(OnboardingProfileDB.user_id == user.id).first()
            if not profile:
                profile = OnboardingProfileDB(
                    user_id=user.id,
                    current_stage=item["current_stage"],
                    preferences={"seeded": True},
                    progress={"facts": item["facts"], "seeded": True},
                    completed_steps=item["completed_steps"],
                    updated_at=now - timedelta(days=item["days_ago"]),
                )
                db.add(profile)
            else:
                profile.current_stage = item["current_stage"]
                profile.preferences = {**(profile.preferences or {}), "seeded": True}
                profile.progress = {**(profile.progress or {}), "facts": item["facts"], "seeded": True}
                profile.completed_steps = item["completed_steps"]
                profile.updated_at = now - timedelta(days=item["days_ago"])

        db.commit()
        return {"created": created, "updated": updated, "total": len(mock_users)}
    
    @staticmethod
    def format_date(date_obj) -> str:
        """Format datetime object to readable string."""
        if not date_obj:
            return "N/A"
        return date_obj.strftime("%Y-%m-%d %H:%M")
    
    @staticmethod
    def get_upload_directory() -> Path:
        """Get or create the upload directory for admin documents."""
        upload_root = Path(__file__).resolve().parent.parent.parent / "Internal rules"
        upload_root.mkdir(parents=True, exist_ok=True)
        return upload_root
    
    @staticmethod
    def save_uploaded_file(file_obj, category: str = "admin", stage: str = "") -> tuple[bool, str, str]:
        """
        Save uploaded file to disk.
        Returns: (success, file_path, upload_id)
        """
        try:
            upload_id = str(uuid.uuid4())
            upload_root = AdminUtils.get_upload_directory()
            
            file_name = str(getattr(file_obj, "name", "uploaded.md"))
            raw = file_obj.getvalue() if hasattr(file_obj, "getvalue") else file_obj.read()
            
            safe_name = Path(file_name).name
            if (upload_root / safe_name).exists():
                stem = Path(file_name).stem
                suffix = Path(file_name).suffix
                safe_name = f"{stem}_{upload_id[:8]}{suffix}"
            
            file_path = upload_root / safe_name
            file_path.write_bytes(raw)
            
            return True, str(file_path), upload_id
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return False, "", ""
    
    @staticmethod
    def extract_pdf_text(pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(pdf_bytes))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF: {e}")
            return ""
    
    @staticmethod
    def get_file_metadata(file_name: str, upload_id: str, category: str, stage: str = "") -> Dict[str, Any]:
        """Create metadata dict for uploaded file."""
        meta = {
            "origin": "admin_upload",
            "upload_id": upload_id,
            "file_name": Path(file_name).name,
            "category": category or "admin",
        }
        if stage:
            meta["stage"] = stage
        return meta
    
    @staticmethod
    def list_uploaded_admin_files(rag_system) -> List[Dict[str, Any]]:
        """List all admin-uploaded files from RAG system."""
        try:
            all_uploads = rag_system.vector_store.list_uploaded_files()
            admin_uploads = [
                u for u in all_uploads 
                if u.get("metadata", {}).get("origin") == "admin_upload"
            ]
            return admin_uploads
        except Exception as e:
            logger.error(f"Error listing uploads: {e}")
            return []
    
    @staticmethod
    def delete_uploaded_file(upload_id: str, rag_system) -> tuple[bool, int]:
        """
        Delete uploaded file from RAG index and disk.
        Returns: (success, chunks_removed)
        """
        try:
            removed = rag_system.vector_store.delete_by_upload_id(str(upload_id or ""))
            
            upload_root = AdminUtils.get_upload_directory()
            deleted_files = 0
            if upload_root.exists() and upload_id:
                for p in upload_root.glob(f"*{upload_id[:8]}*"):
                    try:
                        p.unlink()
                        deleted_files += 1
                    except Exception as e:
                        logger.warning(f"Could not delete {p}: {e}")
            
            return True, removed
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False, 0
    
    @staticmethod
    def pdf_to_base64(pdf_buffer: BytesIO) -> str:
        """Convert PDF buffer to base64 string for embedding in HTML."""
        import base64
        pdf_buffer.seek(0)
        pdf_bytes = pdf_buffer.read()
        return base64.b64encode(pdf_bytes).decode('utf-8')
    
    @staticmethod
    def generate_onboarding_pdf(onboarding_data: Dict[str, Any]) -> BytesIO:
        """
        Generate a summarized onboarding report PDF.
        Returns: BytesIO object containing the PDF
        """
        try:
            pdf_buffer = BytesIO()
            doc = SimpleDocTemplate(
                pdf_buffer,
                pagesize=A4,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            story = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1f3864'),
                spaceAfter=6,
                alignment=1,
            )
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#555555'),
                spaceAfter=16,
                alignment=1,
            )
            section_style = ParagraphStyle(
                'Section',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=colors.white,
                backColor=colors.HexColor('#1f3864'),
                spaceBefore=14,
                spaceAfter=6,
                leftIndent=6,
                borderPadding=(4, 4, 4, 4),
            )
            normal_style = ParagraphStyle(
                'Body',
                parent=styles['Normal'],
                fontSize=9,
                leading=13,
            )

            def make_table(data, col_widths=None):
                if col_widths is None:
                    col_widths = [2.2*inch, 4.3*inch]
                t = Table(data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8edf4')),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a1a1a')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                    ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#f5f7fb'), colors.white]),
                ]))
                return t

            facts = onboarding_data.get("facts", {})
            completed_steps = onboarding_data.get("completed_steps", []) or []
            progress = onboarding_data.get("progress", {}) or {}

            def sanitize_report_text(text: str) -> str:
                """Remove raw URLs/URIs from visible report text."""
                cleaned = re.sub(r'(?:https?|file)://[^\s\)]+', '', str(text or ''))
                cleaned = re.sub(r'\s{2,}', ' ', cleaned)
                return cleaned.strip()

            def extract_stage_summary(stage_key: str) -> str:
                """Return a brief summary of what the newcomer needs to know from this stage."""
                stage_summaries = {
                    "welcome": "Basic profile information and introduction to the company.",
                    "department_info": "Understanding team structure, key contacts, and department workflows.",
                    "key_responsibilities": "Primary duties, performance expectations, and initial tasks.",
                    "tools_systems": "Software, platforms, and access credentials needed for the role.",
                    "training_needs": "Required training modules, certifications, and skill development areas.",
                }
                return stage_summaries.get(stage_key, "")

            def extract_document_links_from_facts() -> Dict[str, Dict[str, List[str]]]:
                links_by_stage: Dict[str, Dict[str, List[str]]] = {}
                for key, value in facts.items():
                    if not isinstance(value, str):
                        continue

                    stage = key.split('.')[0] if '.' in key else 'general'
                    urls = re.findall(r'(?:https?|file)://[^\s\)]+', value)
                    doc_refs = re.findall(
                        r'(?:document|rule|policy|procedure|guideline|handbook)[\s:]+([^\n,\.]+)',
                        value,
                        re.IGNORECASE,
                    )

                    if not urls and not doc_refs:
                        continue

                    if stage not in links_by_stage:
                        links_by_stage[stage] = {"urls": [], "docs": []}

                    links_by_stage[stage]["urls"].extend(urls)
                    cleaned_doc_refs: List[str] = []
                    for doc_ref in doc_refs:
                        cleaned_label = re.sub(r'(?:https?|file)://[^\s\)]+', '', str(doc_ref)).strip(' -:;,.')
                        if cleaned_label:
                            cleaned_doc_refs.append(cleaned_label)
                    links_by_stage[stage]["docs"].extend(cleaned_doc_refs)

                return links_by_stage

            def link_label(url: str) -> str:
                """Return readable link text while preserving full URL target."""
                from urllib.parse import urlparse, unquote

                parsed = urlparse(str(url))
                if parsed.scheme == "file":
                    file_name = Path(unquote(parsed.path)).name
                    if not file_name:
                        return "Open document"
                    file_path = Path(file_name)
                    if file_path.suffix.lower() != ".pdf":
                        return f"{file_path.stem}.pdf"
                    return file_name
                return str(url)

            def pdf_href_for_url(url: str) -> str:
                """Prefer PDF targets for local files so links open as documents."""
                from html import escape
                from urllib.parse import urlparse, unquote

                parsed = urlparse(str(url))
                if parsed.scheme != "file":
                    return str(url)

                source_path = Path(unquote(parsed.path))
                if not source_path.exists():
                    return str(url)

                if source_path.suffix.lower() == ".pdf":
                    return source_path.resolve().as_uri()

                if source_path.suffix.lower() not in {".md", ".markdown", ".txt"}:
                    return str(url)

                try:
                    content = source_path.read_text(encoding="utf-8", errors="replace")
                    if not content.strip():
                        return str(url)

                    cache_dir = Path(__file__).resolve().parent / "generated_resource_pdfs"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    target_pdf = cache_dir / f"{source_path.stem}.pdf"

                    text_lines = [escape(line) for line in content.splitlines()]
                    text_html = "<br/>".join(text_lines) or "(Empty document)"

                    temp_buffer = BytesIO()
                    temp_doc = SimpleDocTemplate(
                        temp_buffer,
                        pagesize=A4,
                        rightMargin=0.75 * inch,
                        leftMargin=0.75 * inch,
                        topMargin=0.75 * inch,
                        bottomMargin=0.75 * inch,
                    )
                    temp_story = [
                        Paragraph(source_path.name, styles['Heading2']),
                        Spacer(1, 0.08 * inch),
                        Paragraph(text_html, normal_style),
                    ]
                    temp_doc.build(temp_story)
                    temp_buffer.seek(0)
                    target_pdf.write_bytes(temp_buffer.read())
                    return target_pdf.resolve().as_uri()
                except Exception as conversion_error:
                    logger.warning(f"Could not convert link target to PDF for {source_path}: {conversion_error}")
                    return str(url)

            # ── Title ──────────────────────────────────────────────
            full_name = onboarding_data.get("full_name") or facts.get("welcome.name", "N/A")
            role = facts.get("welcome.role", onboarding_data.get("current_stage", "N/A"))
            department = facts.get("welcome.department", "N/A")

            story.append(Paragraph("Onboarding Summary", title_style))
            story.append(Paragraph(
                f"Generated: {datetime.now().strftime('%d %B %Y')}",
                subtitle_style,
            ))

            # ── Personal Info ──────────────────────────────────────
            story.append(Paragraph("Employee Information", section_style))
            phone = facts.get("welcome.phone_number", "")
            emergency = facts.get("welcome.emergency_contact", "")
            pronouns = facts.get("welcome.pronouns", "")
            personal_rows = [
                ["Full Name", full_name],
                ["Email", onboarding_data.get("email", "N/A")],
                ["Role", role],
                ["Department", department],
                ["Start Date", AdminUtils.format_date(onboarding_data.get("created_at"))],
                ["Onboarding Status", onboarding_data.get("current_stage", "N/A").replace("_", " ").title()],
            ]
            if phone:
                personal_rows.append(["Phone", phone])
            if emergency:
                personal_rows.append(["Emergency Contact", emergency])
            if pronouns and pronouns.lower() != "none":
                personal_rows.append(["Pronouns", pronouns])
            story.append(make_table(personal_rows))
            story.append(Spacer(1, 0.1*inch))

            # ── Stage Summaries ────────────────────────────────────
            stage_labels = {
                "welcome":              "Welcome & Profile",
                "department_info":      "Department Information",
                "key_responsibilities": "Key Responsibilities",
                "tools_systems":        "Tools & Systems",
                "training_needs":       "Training Needs",
            }

            story.append(Paragraph("Stage Summaries", section_style))

            for stage_key, stage_label in stage_labels.items():
                # Skip welcome stage - it's now in Employee Information
                if stage_key == "welcome":
                    continue
                
                # Check if stage has answers (if there are facts for this stage, it was completed)
                stage_facts = [k for k in facts.keys() if k.startswith(f"{stage_key}.") and not k.endswith("._qlabel")]
                completed = len(stage_facts) > 0
                status = "✓ Completed" if completed else "— Not completed"

                stage_heading_style = ParagraphStyle(
                    f'stage_{stage_key}',
                    parent=styles['Heading3'],
                    fontSize=10,
                    textColor=colors.HexColor('#1f3864') if completed else colors.HexColor('#888888'),
                    spaceBefore=10,
                    spaceAfter=4,
                )
                story.append(Paragraph(f"{stage_label}  —  {status}", stage_heading_style))

                summary = extract_stage_summary(stage_key)
                if summary:
                    story.append(Paragraph(summary, normal_style))
                elif completed:
                    story.append(Paragraph("Stage completed.", normal_style))
                else:
                    story.append(Paragraph("Not yet completed.", normal_style))

                story.append(Spacer(1, 0.05*inch))

            # ── Mentioned Documents & Links ───────────────────────
            links_by_stage = extract_document_links_from_facts()
            if links_by_stage:
                story.append(Spacer(1, 0.08*inch))
                story.append(Paragraph("Mentioned Documents & Links", section_style))

                for stage_key, stage_label in stage_labels.items():
                    stage_data = links_by_stage.get(stage_key)
                    if not stage_data:
                        continue

                    urls = sorted(set(stage_data.get("urls", [])))
                    docs = sorted(set(stage_data.get("docs", [])))
                    if not urls and not docs:
                        continue

                    story.append(Paragraph(stage_label, styles['Heading4']))

                    # Collect document names from URLs to avoid duplicates
                    shown_doc_names = set()
                    
                    def _is_similar_doc_name(doc_name_check: str, shown_names: set) -> bool:
                        """Check if doc_name is similar to any shown name using word overlap."""
                        doc_words = set(doc_name_check.lower().replace('_', ' ').replace('-', ' ').split())
                        for shown in shown_names:
                            shown_words = set(shown.split())
                            common_words = doc_words & shown_words
                            if len(common_words) >= min(2, len(doc_words), len(shown_words)):
                                return True
                        return False
                    
                    for url in urls:
                        safe_url = pdf_href_for_url(url).replace("&", "&amp;")
                        link_text = link_label(url).replace("&", "&amp;")
                        shown_doc_names.add(link_text.lower().replace('_', ' ').replace('-', ' ').replace('.pdf', '').replace('.md', ''))
                        story.append(
                            Paragraph(
                                f'• <link href="{safe_url}" color="blue"><u>{link_text}</u></link>',
                                normal_style,
                            )
                        )

                    # Filter out plain text docs that match URL document names
                    for doc_name in docs:
                        if not _is_similar_doc_name(doc_name, shown_doc_names):
                            story.append(Paragraph(f"• {doc_name}", normal_style))

                    story.append(Spacer(1, 0.04*inch))

            # ── Footer ─────────────────────────────────────────────
            story.append(Spacer(1, 0.2*inch))
            story.append(Paragraph(
                f"Confidential — {full_name} onboarding report — {datetime.now().strftime('%Y-%m-%d')}",
                ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7,
                               textColor=colors.grey, alignment=1),
            ))

            try:
                doc.build(story)
                pdf_buffer.seek(0)
                return pdf_buffer
            except Exception as build_error:
                logger.error(f"Error building PDF document: {build_error}", exc_info=True)
                return None
        except Exception as e:
            logger.error(f"Error generating PDF: {type(e).__name__}: {e}", exc_info=True)
            return None
