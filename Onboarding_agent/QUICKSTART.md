# 🚀 Quick Start Guide

## Installation & Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and add:
- **GOOGLE_API_KEY**: Get from https://aistudio.google.com/app/apikey
- **GOOGLE_OAUTH_CLIENT_ID**: Get from https://console.cloud.google.com/
- **GOOGLE_OAUTH_CLIENT_SECRET**: Get from https://console.cloud.google.com/
- **ADMIN_EMAILS**: Your admin email addresses (comma-separated)

### 3. Start the Application
```bash
streamlit run chat_app.py
```

Open `http://localhost:8501` in your browser.

---

## Using the Application

### For New Users (Onboarding)
1. Click "Sign in with Google"
2. Complete the 5-stage onboarding process
3. Ask questions about company policies - the AI will retrieve answers from internal rules documents
4. Track your progress in the sidebar

### For Admins
1. Login with an admin email (configured in ADMIN_EMAILS)
2. Access the admin dashboard to:
   - View onboarding statistics
   - Manage users and their progress
   - Upload new documentation
   - Check system configuration

### Example Questions to Ask
- "What is IT Administrator Responsibilities?"
- "Explain work environment requirements"
- "What are remote and hybrid work guidelines?"
- "What is the employee code of conduct?"

---

## Key Features

✅ **RAG-Powered**: Answers from 14 internal rules documents with source citations
✅ **Google OAuth**: Secure authentication with Google accounts
✅ **Admin Dashboard**: Manage users and view statistics
✅ **Memory System**: Remembers conversation history and user preferences
✅ **Progress Tracking**: 5-stage onboarding flow with visual progress

---

## Troubleshooting

**Q: Documents not being retrieved?**
- Ensure `../Internal rules/` folder exists with markdown files
- Check that GOOGLE_API_KEY is valid
- Restart the app to reinitialize the vector store

**Q: Google OAuth not working?**
- Verify GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env
- Ensure redirect URI is set to `http://localhost:8501` in Google Cloud Console

**Q: Admin dashboard not showing?**
- Verify your email is in ADMIN_EMAILS in .env
- Logout and login again after updating .env

---

## Documentation

- **README.md** - Full documentation and architecture
- **AUTHENTICATION_GUIDE.md** - Google OAuth setup details
- **GMAIL_OAUTH_SETUP.md** - Step-by-step OAuth configuration
- **ADMIN_PANEL_GUIDE.md** - Admin dashboard features

---

## Support

For issues or questions, refer to the main README.md for detailed technical documentation.
