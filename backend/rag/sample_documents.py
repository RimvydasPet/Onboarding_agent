"""Sample onboarding documents for the RAG system."""

ONBOARDING_DOCUMENTS = [
    {
        "content": """Welcome to Our Platform!

We're excited to have you here. This guide will help you get started with your account and explore all the features available to you.

Getting started is easy:
1. Complete your profile setup
2. Explore the dashboard
3. Connect with your team
4. Start your first project

If you need any help along the way, our support team is here for you 24/7.""",
        "metadata": {
            "source": "welcome_guide",
            "category": "getting_started",
            "topic": "welcome"
        }
    },
    {
        "content": """Account Setup Guide

Creating your account is the first step to accessing all our features.

Step 1: Verify Your Email
Check your inbox for a verification email and click the link to activate your account.

Step 2: Set Up Your Profile
- Add your full name
- Upload a profile picture
- Set your timezone
- Choose your notification preferences

Step 3: Security Settings
- Enable two-factor authentication (recommended)
- Set up a strong password
- Add recovery email

Your account security is our top priority.""",
        "metadata": {
            "source": "account_setup",
            "category": "getting_started",
            "topic": "account"
        }
    },
    {
        "content": """Dashboard Overview

Your dashboard is your central hub for all activities.

Main Sections:
- Overview: See your recent activity and important updates
- Projects: Access and manage your projects
- Team: Collaborate with team members
- Analytics: View performance metrics
- Settings: Customize your experience

Quick Actions:
You can quickly create new projects, invite team members, or access recent files from the dashboard toolbar.

Customization:
Drag and drop widgets to personalize your dashboard layout.""",
        "metadata": {
            "source": "dashboard_guide",
            "category": "features",
            "topic": "dashboard"
        }
    },
    {
        "content": """Creating Your First Project

Projects help you organize your work and collaborate with others.

To create a project:
1. Click the "New Project" button in the dashboard
2. Enter a project name and description
3. Choose a template (optional)
4. Invite team members
5. Set project permissions
6. Click "Create"

Project Templates:
- Marketing Campaign
- Product Development
- Event Planning
- Custom (start from scratch)

Best Practices:
- Use clear, descriptive project names
- Add detailed descriptions
- Set realistic deadlines
- Invite relevant team members from the start""",
        "metadata": {
            "source": "project_creation",
            "category": "features",
            "topic": "projects"
        }
    },
    {
        "content": """Team Collaboration Features

Work together seamlessly with your team.

Communication Tools:
- Real-time chat
- Video conferencing
- Comments and mentions
- Activity feeds

File Sharing:
Upload and share files up to 100MB. Supported formats include documents, images, videos, and more.

Permissions:
- Owner: Full control
- Admin: Manage members and settings
- Member: View and edit
- Guest: View only

Notifications:
Stay updated with customizable notifications for mentions, comments, and project updates.""",
        "metadata": {
            "source": "collaboration_guide",
            "category": "features",
            "topic": "collaboration"
        }
    },
    {
        "content": """Troubleshooting Common Issues

Can't log in?
- Check your email and password
- Try resetting your password
- Clear your browser cache
- Disable browser extensions

Email not verified?
- Check your spam folder
- Request a new verification email
- Contact support if issues persist

Performance issues?
- Clear browser cache
- Try a different browser
- Check your internet connection
- Disable unnecessary browser extensions

Still having problems?
Contact our support team at support@platform.com or use the in-app chat.""",
        "metadata": {
            "source": "troubleshooting",
            "category": "support",
            "topic": "troubleshooting"
        }
    },
    {
        "content": """Privacy and Security

We take your privacy seriously.

Data Protection:
- All data is encrypted in transit and at rest
- Regular security audits
- GDPR and CCPA compliant
- No data sharing with third parties without consent

Your Rights:
- Access your data anytime
- Request data deletion
- Export your data
- Control privacy settings

Security Features:
- Two-factor authentication
- Session management
- Login activity monitoring
- Automatic logout after inactivity

For more information, review our Privacy Policy and Terms of Service.""",
        "metadata": {
            "source": "privacy_security",
            "category": "legal",
            "topic": "security"
        }
    },
    {
        "content": """Mobile App Guide

Access your account on the go with our mobile app.

Available on:
- iOS (iPhone and iPad)
- Android

Key Features:
- Full dashboard access
- Push notifications
- Offline mode
- File upload from camera
- Quick actions

Download:
Search for "Our Platform" in the App Store or Google Play Store.

Syncing:
All changes sync automatically across devices. Work on mobile and continue on desktop seamlessly.

Mobile-Specific Tips:
- Enable push notifications for important updates
- Use offline mode when traveling
- Take advantage of camera integration for quick uploads""",
        "metadata": {
            "source": "mobile_app",
            "category": "features",
            "topic": "mobile"
        }
    },
    {
        "content": """Keyboard Shortcuts

Work faster with keyboard shortcuts.

Navigation:
- Ctrl/Cmd + K: Quick search
- Ctrl/Cmd + /: Show shortcuts
- Ctrl/Cmd + H: Go to home

Projects:
- Ctrl/Cmd + N: New project
- Ctrl/Cmd + E: Edit project
- Ctrl/Cmd + D: Duplicate project

General:
- Ctrl/Cmd + S: Save
- Ctrl/Cmd + Z: Undo
- Ctrl/Cmd + Shift + Z: Redo
- Esc: Close modal

Customize:
You can customize shortcuts in Settings > Keyboard Shortcuts.""",
        "metadata": {
            "source": "keyboard_shortcuts",
            "category": "features",
            "topic": "productivity"
        }
    },
    {
        "content": """Billing and Subscriptions

Manage your subscription and billing.

Plans:
- Free: Basic features for individuals
- Pro: Advanced features for professionals ($9.99/month)
- Team: Collaboration tools for teams ($29.99/month)
- Enterprise: Custom solutions (contact sales)

Payment Methods:
- Credit/Debit cards
- PayPal
- Bank transfer (Enterprise only)

Billing Cycle:
- Monthly or annual billing
- Annual plans save 20%
- Cancel anytime, no penalties

Invoices:
Access all invoices in Settings > Billing. Download as PDF for your records.

Upgrades:
Upgrade or downgrade your plan anytime. Changes take effect immediately.""",
        "metadata": {
            "source": "billing_guide",
            "category": "account",
            "topic": "billing"
        }
    }
]


def get_sample_documents():
    """Return sample onboarding documents."""
    return ONBOARDING_DOCUMENTS


def get_documents_by_category(category: str):
    """Get documents filtered by category."""
    return [doc for doc in ONBOARDING_DOCUMENTS if doc["metadata"]["category"] == category]


def get_documents_by_topic(topic: str):
    """Get documents filtered by topic."""
    return [doc for doc in ONBOARDING_DOCUMENTS if doc["metadata"]["topic"] == topic]
