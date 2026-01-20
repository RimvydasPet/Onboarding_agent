from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime
from typing import Dict, List, Optional
import io
import logging

logger = logging.getLogger(__name__)


class OnboardingPDFGenerator:
    """Generate PDF summaries for onboarding sessions."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Check if styles already exist before adding them
        if 'CustomTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ))
        
        if 'SectionHeader' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHeader',
                parent=self.styles['Heading2'],
                fontSize=16,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=12,
                spaceBefore=12,
                fontName='Helvetica-Bold'
            ))
        
        if 'SubHeader' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SubHeader',
                parent=self.styles['Heading3'],
                fontSize=12,
                textColor=colors.HexColor('#34495e'),
                spaceAfter=6,
                fontName='Helvetica-Bold'
            ))
        
        # Check if BodyText already exists before adding
        if 'BodyText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='BodyText',
                parent=self.styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=8,
                alignment=TA_LEFT
            ))
    
    def generate_onboarding_summary(
        self,
        user_data: Dict,
        tasks_data: Dict[str, List[Dict]],
        output_path: Optional[str] = None
    ) -> bytes:
        """
        Generate a comprehensive onboarding summary PDF.
        
        Args:
            user_data: Dictionary containing user information
            tasks_data: Dictionary mapping stages to task lists
            output_path: Optional file path to save PDF. If None, returns bytes.
        
        Returns:
            PDF as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        # Title
        story.append(Paragraph("Onboarding Summary", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2 * inch))
        
        # User Information Section
        story.extend(self._create_user_info_section(user_data))
        story.append(Spacer(1, 0.3 * inch))
        
        # Key Points Section
        story.extend(self._create_key_points_section(tasks_data.get('welcome', [])))
        story.append(Spacer(1, 0.3 * inch))
        
        # Office & Perks Section
        story.extend(self._create_office_perks_section(tasks_data.get('welcome', [])))
        story.append(Spacer(1, 0.3 * inch))
        
        # Tasks Progress Section
        story.extend(self._create_tasks_section(tasks_data))
        story.append(Spacer(1, 0.3 * inch))
        
        # Footer
        story.extend(self._create_footer())
        
        # Build PDF
        doc.build(story)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            logger.info(f"PDF saved to {output_path}")
        
        return pdf_bytes
    
    def _create_user_info_section(self, user_data: Dict) -> List:
        """Create user information section."""
        elements = []
        
        elements.append(Paragraph("Employee Information", self.styles['SectionHeader']))
        
        info_data = [
            ['Name:', user_data.get('name', 'N/A')],
            ['Role:', user_data.get('role', 'N/A')],
            ['Email:', user_data.get('email', 'N/A')],
            ['Onboarding Date:', datetime.now().strftime('%B %d, %Y')]
        ]
        
        table = Table(info_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        
        return elements
    
    def _create_key_points_section(self, welcome_tasks: List[Dict]) -> List:
        """Create key points summary section."""
        elements = []
        
        elements.append(Paragraph("Key Points - What You Need to Know", self.styles['SectionHeader']))
        
        # Extract key information from tasks
        key_points = []
        
        for task in welcome_tasks:
            task_id = task.get('task_id', '')
            completion_data = task.get('completion_data', {})
            
            if task_id == 'role_shared' and completion_data:
                role = completion_data.get('response', '')
                if role:
                    key_points.append(f"• You're joining us as: {role}")
            
            elif task_id == 'office_location' and completion_data:
                location = completion_data.get('response', '')
                if location:
                    key_points.append(f"• Your work arrangement: {location}")
            
            elif task_id == 'work_schedule' and completion_data:
                schedule = completion_data.get('response', '')
                if schedule:
                    key_points.append(f"• Preferred schedule: {schedule}")
            
            elif task_id == 'perks_interest' and completion_data:
                perks = completion_data.get('response', '')
                if perks:
                    key_points.append(f"• Interested in perks: {perks}")
            
            elif task_id == 'equipment_needs' and completion_data:
                equipment = completion_data.get('response', '')
                if equipment:
                    key_points.append(f"• Equipment requested: {equipment}")
        
        if key_points:
            for point in key_points:
                elements.append(Paragraph(point, self.styles['BodyText']))
        else:
            elements.append(Paragraph(
                "Complete the welcome stage questions to see your personalized summary here.",
                self.styles['BodyText']
            ))
        
        # Add general onboarding tips
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("Important Reminders:", self.styles['SubHeader']))
        
        tips = [
            "• Review your office location and work schedule preferences above",
            "• Contact HR to activate your selected perks and benefits",
            "• IT will set up your equipment based on your specifications",
            "• Complete all onboarding stages to unlock full platform access",
            "• Reach out to your manager with any questions or concerns"
        ]
        
        for tip in tips:
            elements.append(Paragraph(tip, self.styles['BodyText']))
        
        return elements
    
    def _create_office_perks_section(self, welcome_tasks: List[Dict]) -> List:
        """Create office and perks information section."""
        elements = []
        
        elements.append(Paragraph("Office & Perks Preferences", self.styles['SectionHeader']))
        
        # Extract office and perks related data from task completion data
        office_perks_data = []
        
        for task in welcome_tasks:
            task_id = task.get('task_id', '')
            completion_data = task.get('completion_data', {})
            
            if task_id == 'office_location' and completion_data:
                office_perks_data.append([
                    'Office Location:',
                    completion_data.get('response', 'Not specified')
                ])
            elif task_id == 'work_schedule' and completion_data:
                office_perks_data.append([
                    'Work Schedule:',
                    completion_data.get('response', 'Not specified')
                ])
            elif task_id == 'perks_interest' and completion_data:
                office_perks_data.append([
                    'Perks Interest:',
                    completion_data.get('response', 'Not specified')
                ])
            elif task_id == 'equipment_needs' and completion_data:
                office_perks_data.append([
                    'Equipment Needs:',
                    completion_data.get('response', 'Not specified')
                ])
        
        if not office_perks_data:
            elements.append(Paragraph(
                "No office and perks information collected yet.",
                self.styles['BodyText']
            ))
        else:
            table = Table(office_perks_data, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
                ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#34495e')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ecf0f1')),
            ]))
            elements.append(table)
        
        return elements
    
    def _create_tasks_section(self, tasks_data: Dict[str, List[Dict]]) -> List:
        """Create tasks progress section."""
        elements = []
        
        elements.append(Paragraph("Onboarding Progress", self.styles['SectionHeader']))
        
        for stage, tasks in tasks_data.items():
            if not tasks:
                continue
            
            # Stage header
            stage_title = stage.replace('_', ' ').title()
            elements.append(Paragraph(stage_title, self.styles['SubHeader']))
            
            # Calculate progress
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.get('completed', False))
            required_tasks = [t for t in tasks if not t.get('optional', False)]
            required_completed = sum(1 for t in required_tasks if t.get('completed', False))
            
            # Progress summary
            progress_text = f"Progress: {completed_tasks}/{total_tasks} tasks completed "
            progress_text += f"({required_completed}/{len(required_tasks)} required)"
            elements.append(Paragraph(progress_text, self.styles['BodyText']))
            
            # Task table
            task_data = [['Task', 'Status', 'Type']]
            for task in tasks:
                task_data.append([
                    task.get('description', 'N/A'),
                    '✓ Completed' if task.get('completed', False) else '○ Pending',
                    'Optional' if task.get('optional', False) else 'Required'
                ])
            
            table = Table(task_data, colWidths=[3.5*inch, 1.5*inch, 1*inch])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.2 * inch))
        
        return elements
    
    def _create_footer(self) -> List:
        """Create PDF footer."""
        elements = []
        
        elements.append(Spacer(1, 0.5 * inch))
        footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        elements.append(Paragraph(footer_text, self.styles['BodyText']))
        
        return elements
