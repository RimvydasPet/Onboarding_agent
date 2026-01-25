from typing import List
from langchain_core.documents import Document


def get_sample_documents() -> List[Document]:
    """
    Get sample onboarding documents for the knowledge base.
    
    Returns:
        List of Document objects with onboarding content
    """
    documents = [
        Document(
            page_content="""
            Welcome to TechVenture Solutions!
            
            We're excited to have you join our platform. TechVenture Solutions is a comprehensive 
            project management and collaboration platform designed to help teams work more efficiently.
            
            Our mission is to empower teams to achieve their goals through innovative technology 
            and seamless collaboration tools. Whether you're managing a small team or a large 
            enterprise, we have the features you need to succeed.
            
            Key benefits of TechVenture Solutions:
            - Real-time collaboration across teams
            - Advanced project tracking and analytics
            - Secure cloud storage with 99.9% uptime
            - Integration with 100+ popular tools
            - 24/7 customer support
            """,
            metadata={
                "source": "welcome_guide",
                "category": "introduction",
                "stage": "welcome"
            }
        ),
        Document(
            page_content="""
            Getting Started with Your Account
            
            Step 1: Complete Your Profile
            - Add your full name and profile picture
            - Set your job title and department
            - Configure your notification preferences
            - Choose your timezone
            
            Step 2: Verify Your Email
            - Check your inbox for a verification email
            - Click the verification link
            - Your account will be fully activated
            
            Step 3: Set Up Two-Factor Authentication (Recommended)
            - Go to Settings > Security
            - Enable 2FA using your preferred method (SMS or authenticator app)
            - Save your backup codes in a secure location
            
            Step 4: Customize Your Dashboard
            - Choose your preferred layout
            - Add widgets for quick access to important features
            - Set up your personal workspace
            """,
            metadata={
                "source": "account_setup_guide",
                "category": "setup",
                "stage": "profile_setup"
            }
        ),
        Document(
            page_content="""
            Creating Your First Project
            
            Projects are the foundation of TechVenture Solutions. Here's how to create one:
            
            1. Click the "New Project" button in the top navigation
            2. Enter your project name and description
            3. Choose a project template (Agile, Waterfall, or Custom)
            4. Invite team members by email
            5. Set project milestones and deadlines
            6. Configure project permissions and visibility
            
            Project Templates:
            - Agile: Perfect for software development with sprints and backlogs
            - Waterfall: Traditional project management with sequential phases
            - Custom: Build your own workflow from scratch
            
            Best Practices:
            - Start with a clear project goal
            - Break down work into manageable tasks
            - Assign clear ownership for each task
            - Set realistic deadlines
            - Review progress regularly
            """,
            metadata={
                "source": "project_guide",
                "category": "projects",
                "stage": "first_steps"
            }
        ),
        Document(
            page_content="""
            Collaboration Features
            
            Real-Time Chat:
            - Direct messages with team members
            - Group channels for projects and teams
            - File sharing in conversations
            - Video and voice calls
            - Screen sharing capabilities
            
            Document Collaboration:
            - Simultaneous editing with multiple users
            - Version history and rollback
            - Comments and suggestions
            - @mentions to notify team members
            - Export to PDF, Word, or Google Docs
            
            Task Management:
            - Create and assign tasks
            - Set priorities and due dates
            - Track task progress with status updates
            - Add subtasks and checklists
            - Attach files and links to tasks
            
            Calendar Integration:
            - Sync with Google Calendar, Outlook, or Apple Calendar
            - Schedule meetings and events
            - Set reminders and notifications
            - View team availability
            """,
            metadata={
                "source": "collaboration_guide",
                "category": "features",
                "stage": "first_steps"
            }
        ),
        Document(
            page_content="""
            Integrations and Extensions
            
            TechVenture Solutions integrates with over 100 popular tools:
            
            Development Tools:
            - GitHub, GitLab, Bitbucket
            - Jira, Linear, Asana
            - Jenkins, CircleCI, Travis CI
            
            Communication:
            - Slack, Microsoft Teams
            - Zoom, Google Meet
            - Discord, Telegram
            
            Cloud Storage:
            - Google Drive, Dropbox
            - OneDrive, Box
            - AWS S3, Azure Blob Storage
            
            Analytics:
            - Google Analytics
            - Mixpanel, Amplitude
            - Tableau, Power BI
            
            How to Add Integrations:
            1. Go to Settings > Integrations
            2. Browse available integrations
            3. Click "Connect" on your desired integration
            4. Authorize access
            5. Configure integration settings
            
            Custom Integrations:
            - Use our REST API for custom integrations
            - Webhooks for real-time events
            - OAuth 2.0 authentication
            - Comprehensive API documentation available
            """,
            metadata={
                "source": "integrations_guide",
                "category": "integrations",
                "stage": "learning_preferences"
            }
        ),
        Document(
            page_content="""
            Security and Privacy
            
            Data Security:
            - End-to-end encryption for all data
            - SOC 2 Type II certified
            - GDPR and CCPA compliant
            - Regular security audits
            - Penetration testing quarterly
            
            Access Control:
            - Role-based access control (RBAC)
            - Single Sign-On (SSO) support
            - IP whitelisting
            - Session management
            - Audit logs for all activities
            
            Data Privacy:
            - Your data is never shared with third parties
            - Data residency options (US, EU, Asia)
            - Right to data portability
            - Right to deletion
            - Transparent privacy policy
            
            Backup and Recovery:
            - Automatic daily backups
            - 30-day backup retention
            - Point-in-time recovery
            - Disaster recovery plan
            - 99.9% uptime SLA
            """,
            metadata={
                "source": "security_guide",
                "category": "security",
                "stage": "learning_preferences"
            }
        ),
        Document(
            page_content="""
            Pricing and Plans
            
            Free Plan:
            - Up to 5 team members
            - 3 projects
            - 5GB storage
            - Basic features
            - Community support
            
            Pro Plan ($15/user/month):
            - Unlimited team members
            - Unlimited projects
            - 100GB storage per user
            - Advanced features
            - Priority email support
            - Custom integrations
            
            Enterprise Plan (Custom pricing):
            - Everything in Pro
            - Unlimited storage
            - Dedicated account manager
            - 24/7 phone support
            - Custom SLA
            - On-premise deployment option
            - Advanced security features
            - Custom training sessions
            
            Billing:
            - Monthly or annual billing
            - Annual plans get 20% discount
            - Cancel anytime, no long-term contracts
            - Prorated refunds available
            - Multiple payment methods accepted
            """,
            metadata={
                "source": "pricing_guide",
                "category": "pricing",
                "stage": "welcome"
            }
        ),
        Document(
            page_content="""
            Support and Resources
            
            Getting Help:
            - Help Center: Comprehensive articles and guides
            - Video Tutorials: Step-by-step video walkthroughs
            - Community Forum: Connect with other users
            - Live Chat: Available 9 AM - 5 PM EST
            - Email Support: support@techventure.com
            - Phone Support: Enterprise customers only
            
            Training Resources:
            - Weekly webinars on new features
            - On-demand training courses
            - Certification program
            - Best practices guides
            - Case studies and success stories
            
            Developer Resources:
            - API Documentation
            - SDK libraries (Python, JavaScript, Ruby)
            - Code examples and tutorials
            - Developer community
            - Sandbox environment for testing
            
            Status and Updates:
            - System status page: status.techventure.com
            - Planned maintenance notifications
            - Feature release notes
            - Product roadmap
            - Monthly newsletter
            """,
            metadata={
                "source": "support_guide",
                "category": "support",
                "stage": "completed"
            }
        ),
        Document(
            page_content="""
            Mobile Apps
            
            TechVenture Solutions is available on iOS and Android:
            
            iOS App Features:
            - Native iOS design
            - Face ID / Touch ID support
            - Offline mode
            - Push notifications
            - Widget support
            - Apple Watch companion app
            
            Android App Features:
            - Material Design
            - Fingerprint authentication
            - Offline mode
            - Push notifications
            - Home screen widgets
            - Android Wear support
            
            Mobile-Specific Features:
            - Quick actions from notifications
            - Voice commands
            - Camera integration for document scanning
            - Location-based reminders
            - Dark mode support
            
            Download:
            - iOS: Available on the App Store
            - Android: Available on Google Play
            - Minimum requirements: iOS 14+ or Android 8+
            """,
            metadata={
                "source": "mobile_guide",
                "category": "mobile",
                "stage": "first_steps"
            }
        ),
        Document(
            page_content="""
            Keyboard Shortcuts
            
            Navigation:
            - Ctrl/Cmd + K: Quick search
            - Ctrl/Cmd + /: Show all shortcuts
            - Ctrl/Cmd + B: Toggle sidebar
            - Ctrl/Cmd + .: Open settings
            
            Project Management:
            - N: Create new task
            - Ctrl/Cmd + N: Create new project
            - E: Edit selected item
            - Del: Delete selected item
            - Ctrl/Cmd + Enter: Save changes
            
            Communication:
            - Ctrl/Cmd + M: New message
            - Ctrl/Cmd + Shift + M: New group chat
            - Ctrl/Cmd + F: Search in conversation
            - Esc: Close current dialog
            
            Formatting:
            - Ctrl/Cmd + B: Bold
            - Ctrl/Cmd + I: Italic
            - Ctrl/Cmd + U: Underline
            - Ctrl/Cmd + Shift + X: Strikethrough
            - Ctrl/Cmd + K: Insert link
            
            Productivity:
            - Ctrl/Cmd + Z: Undo
            - Ctrl/Cmd + Shift + Z: Redo
            - Ctrl/Cmd + C: Copy
            - Ctrl/Cmd + V: Paste
            - Ctrl/Cmd + A: Select all
            """,
            metadata={
                "source": "shortcuts_guide",
                "category": "productivity",
                "stage": "completed"
            }
        )
    ]
    
    return documents
