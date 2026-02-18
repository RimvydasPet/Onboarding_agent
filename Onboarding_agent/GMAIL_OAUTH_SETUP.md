# Gmail OAuth Setup Guide

This guide will help you set up Gmail OAuth 2.0 authentication for the Onboarding Assistant application.

## Prerequisites

- A Google Cloud Project (create one at [Google Cloud Console](https://console.cloud.google.com/))
- Admin access to the Google Cloud Project
- The Onboarding Assistant application running locally or deployed

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click "NEW PROJECT"
4. Enter a project name (e.g., "Onboarding Assistant")
5. Click "CREATE"
6. Wait for the project to be created (this may take a minute)

## Step 2: Enable Google+ API

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google+ API"
3. Click on "Google+ API"
4. Click "ENABLE"

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click "CREATE CREDENTIALS" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen first:
   - Click "CONFIGURE CONSENT SCREEN"
   - Select "External" for User Type
   - Click "CREATE"
   - Fill in the required fields:
     - **App name**: "Onboarding Assistant"
     - **User support email**: Your email
     - **Developer contact information**: Your email
   - Click "SAVE AND CONTINUE"
   - Skip optional scopes and click "SAVE AND CONTINUE"
   - Click "BACK TO DASHBOARD"

4. Now create the OAuth client ID:
   - Go to **APIs & Services** > **Credentials**
   - Click "CREATE CREDENTIALS" > "OAuth client ID"
   - Select "Web application" as the Application type
   - Enter a name (e.g., "Onboarding Assistant Web Client")
   - Under "Authorized redirect URIs", click "ADD URI"
   - Add the following URIs:
     - `http://localhost:8501` (for local development)
     - `http://localhost:8501/` (with trailing slash)
     - If deploying to production, add your production URL (e.g., `https://yourdomain.com`)
   - Click "CREATE"

## Step 4: Copy Credentials

1. After creating the OAuth client ID, a dialog will appear with your credentials
2. Copy the **Client ID** and **Client Secret**
3. Keep these secure - never commit them to version control

## Step 5: Configure Environment Variables

1. Open your `.env` file in the Onboarding_agent directory
2. Add the following lines:

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_here
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501
```

3. Replace `your_client_id_here` and `your_client_secret_here` with the values you copied
4. Save the file

## Step 6: Install Dependencies

Run the following command to install the required OAuth dependencies:

```bash
pip install -r requirements.txt
```

## Step 7: Configure Admin Emails

1. In your `.env` file, add the admin email addresses:

```bash
# Admin Configuration
ADMIN_EMAILS=admin@company.com,hr@company.com
```

2. Replace with your actual admin email addresses (comma-separated)

## Step 8: Start the Application

1. Restart the Streamlit application:

```bash
streamlit run chat_app.py
```

2. The application should now show a "Sign in with Google" button
3. Click the button to authenticate with your Google account

## Testing the Setup

1. **Test User Login:**
   - Click "Sign in with Google"
   - Sign in with your Google account
   - You should be redirected back to the app and see your profile information

2. **Test Admin Features:**
   - If your email is in `ADMIN_EMAILS`, you should see:
     - "Developers info" section in the sidebar
     - "RAG Status" display
     - Comprehensive onboarding summary PDF option
   - If your email is NOT in `ADMIN_EMAILS`, you should see:
     - Clean, simplified interface
     - User-friendly "Your Resources" PDF option
     - On-screen document links display

3. **Test Logout:**
   - Click the logout button (🚪) in the sidebar
   - You should be redirected to the login page

## Troubleshooting

### "Google OAuth is not configured" error

**Solution:** Make sure you've added `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` to your `.env` file and restarted the application.

### "Redirect URI mismatch" error

**Solution:** 
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Go to **APIs & Services** > **Credentials**
3. Click on your OAuth client ID
4. Make sure the redirect URI in the app matches exactly with the one in Google Cloud Console
5. Common redirect URIs:
   - Local: `http://localhost:8501`
   - Production: `https://yourdomain.com`

### "Invalid Client" error

**Solution:** 
1. Double-check that your Client ID and Client Secret are correct
2. Make sure there are no extra spaces or characters
3. Verify the credentials haven't been revoked in Google Cloud Console

### User not recognized as admin

**Solution:**
1. Check that the user's email exactly matches an entry in `ADMIN_EMAILS`
2. Email comparison is case-insensitive, but make sure there are no typos
3. Restart the application after updating `ADMIN_EMAILS`

## Production Deployment

When deploying to production:

1. Update `GOOGLE_OAUTH_REDIRECT_URI` to your production URL:
   ```bash
   GOOGLE_OAUTH_REDIRECT_URI=https://yourdomain.com
   ```

2. Add your production URL to the OAuth consent screen:
   - Go to **APIs & Services** > **Credentials**
   - Click on your OAuth client ID
   - Add `https://yourdomain.com` to "Authorized redirect URIs"

3. Update the OAuth consent screen to show your production app information

4. Consider using environment-specific configuration for different deployment stages

## Security Best Practices

1. **Never commit credentials to version control** - Keep `.env` files in `.gitignore`
2. **Use environment variables** - Don't hardcode credentials in the application
3. **Rotate credentials regularly** - Regenerate OAuth credentials periodically
4. **Monitor API usage** - Check Google Cloud Console for unusual activity
5. **Limit admin emails** - Only add necessary admin emails to `ADMIN_EMAILS`
6. **Use HTTPS in production** - Always use HTTPS for production deployments

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
