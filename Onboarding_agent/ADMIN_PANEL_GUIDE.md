# Admin Panel Architecture

## Overview
The admin panel has been redesigned and separated into modular components for better maintainability and organization.

## Module Structure

### 1. `backend/admin/__init__.py`
Empty init file for the admin package.

### 2. `backend/admin/queries.py`
**Purpose:** Database queries for admin operations

**Key Classes:**
- `AdminQueries` - Static methods for database operations
  - `get_all_onboarded_users()` - Retrieve all completed onboarding users
  - `get_onboarding_stats()` - Get completion statistics
  - `get_user_by_email()` - Fetch user details
  - `get_recent_onboarded_users()` - Get recently onboarded users

### 3. `backend/admin/utils.py`
**Purpose:** Utility functions for admin operations

**Key Classes:**
- `AdminUtils` - Static utility methods
  - `format_date()` - Format datetime objects
  - `get_upload_directory()` - Get/create upload directory
  - `save_uploaded_file()` - Save files to disk
  - `extract_pdf_text()` - Extract text from PDFs
  - `get_file_metadata()` - Create metadata for uploads
  - `list_uploaded_admin_files()` - List admin uploads from RAG
  - `delete_uploaded_file()` - Delete files from index and disk

### 4. `backend/admin/dashboard.py`
**Purpose:** Admin dashboard UI components

**Key Classes:**
- `AdminDashboard` - Static methods for rendering UI
  - `render_developers_info()` - Always-visible developer info (sidebar)
  - `render_onboarded_newcomers()` - Recent onboarded users list
  - `render_all_onboarded_users()` - Full onboarded users table
  - `render_documentation_upload()` - Document upload interface
  - `render_system_status()` - System health checks

## Admin Panel Flow

### When Admin Logs In:
1. User authenticates via OAuth
2. System checks if user email is in `ADMIN_EMAILS` (from config)
3. If admin:
   - Admin dashboard is displayed instead of onboarding flow
   - `st.stop()` prevents onboarding UI from rendering
4. If regular user:
   - Normal onboarding flow continues

### Admin Dashboard Tabs:

#### 📊 Overview Tab
- System status (RAG, Web Search)
- Quick stats (Total users, Completed, In Progress, Completion Rate)

#### 👥 Newcomers Tab
- Recent onboarded users (last 15)
- View all onboarded users option
- User details: Name, Email, Role, Department, Completion Date

#### 📚 Documentation Tab
- **Upload Documents:** Add company docs with categories and stage assignment
- **Manage Files:** View, delete, and manage uploaded documents

#### 🔧 System Tab
- RAG configuration and indexed document count
- API configuration (Web Search provider, API key status)

### Sidebar (Always Visible for Admins):
- **Developers Info** (not in dropdown):
  - Session ID
  - Indexed documents count
  - AI Mode status
  - Web Search provider

## Configuration

### Admin Setup
Set admin emails in `.env`:
```
ADMIN_EMAILS=admin@company.com,manager@company.com
```

### File Upload
- Uploads are saved to: `Internal rules/` directory
- Metadata includes: origin, upload_id, file_name, category, stage
- Supported formats: .md, .pdf, .txt

## Key Features Removed from Admin Login
- ❌ Onboarding process (stages, progress tracking)
- ❌ Revisit stage functionality
- ❌ Onboarding assistant features
- ❌ Developer info in dropdown (now always visible)

## Key Features Added
- ✅ Always-visible developers info
- ✅ Onboarded newcomers dashboard
- ✅ Company documentation upload with categories
- ✅ File management (delete, view details)
- ✅ System status and health checks
- ✅ Completion statistics and analytics

## Integration in chat_app.py

```python
# Imports
from backend.admin.dashboard import AdminDashboard
from backend.admin.queries import AdminQueries
from backend.admin.utils import AdminUtils

# Admin detection (after authentication)
_is_admin_user = _is_user_admin(st.session_state.user_email)

if _is_admin_user:
    rag = initialize_system()
    db = next(get_db())
    
    # Render admin dashboard
    AdminDashboard.render_developers_info(rag, st.session_state)
    # ... render tabs ...
    st.stop()  # Prevent onboarding UI
```

## Usage Examples

### Get Onboarding Stats
```python
from backend.admin.queries import AdminQueries
stats = AdminQueries.get_onboarding_stats(db)
print(f"Completed: {stats['completed_users']}")
```

### Upload Document
```python
from backend.admin.utils import AdminUtils
success, path, upload_id = AdminUtils.save_uploaded_file(
    file_obj, 
    category="policies"
)
```

### Delete Uploaded File
```python
success, removed = AdminUtils.delete_uploaded_file(upload_id, rag_system)
```

## Future Enhancements
- User management (activate/deactivate users)
- Activity logs and audit trails
- Bulk user actions
- Advanced analytics and reporting
- Document search analytics
- Admin settings and preferences
