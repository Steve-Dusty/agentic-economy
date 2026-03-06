# Google OAuth Setup for Trinity

## Quick Setup

To enable Google OAuth (Gmail, Calendar, Drive) in Trinity, you need to configure OAuth credentials in Google Cloud Console.

### Steps:

1. **Go to Google Cloud Console**
   - URL: https://console.cloud.google.com/apis/credentials
   - Select or create your project

2. **Create OAuth 2.0 Client ID**
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Name: `Trinity Agent Platform`

3. **Add Authorized Redirect URIs**

   For local development:
   ```
   http://localhost:8000/api/oauth/google/callback
   ```

   For production (replace with your domain):
   ```
   https://your-domain.com/api/oauth/google/callback
   ```

4. **Get Credentials**
   - Copy the **Client ID**
   - Copy the **Client Secret**

5. **Configure Trinity**

   Add to your `.env` file:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

6. **Restart Services**
   ```bash
   docker-compose restart backend
   ```

---

## Configure OAuth Consent Screen

1. Go to https://console.cloud.google.com/apis/credentials/consent
2. User Type: **Internal** (for organization only) or **External** (for public)
3. App name: `Trinity Agent Platform`
4. User support email: Your email
5. Authorized domains: Your domain

### Required Scopes

Add these scopes for Trinity agents:

- `https://www.googleapis.com/auth/gmail.readonly` - Read Gmail
- `https://www.googleapis.com/auth/calendar` - Google Calendar access
- `https://www.googleapis.com/auth/drive.readonly` - Read Google Drive

Optional scopes (add as needed):
- `https://www.googleapis.com/auth/drive` - Full Drive access (read/write)
- `https://www.googleapis.com/auth/documents` - Google Docs
- `https://www.googleapis.com/auth/spreadsheets` - Google Sheets

---

## Testing the OAuth Flow

1. Go to `http://localhost:3000/credentials` (or your production URL)
2. Click "Connect Google"
3. Authorize with your Google account
4. Should redirect back to credentials page
5. Credential should appear in the list

---

## Troubleshooting

### "Invalid or expired OAuth state"
**Cause:** Backend URL doesn't match the redirect URI in state
**Fix:** Ensure `BACKEND_URL` in `.env` matches your environment

### "Redirect URI mismatch"
**Cause:** The redirect URI is not registered in Google Cloud Console
**Fix:** Add the redirect URI to "Authorized redirect URIs" in Google Cloud Console

### "Access blocked: This app's request is invalid"
**Cause:** Scopes not configured in OAuth consent screen
**Fix:** Add required scopes in Google Cloud Console

### "This app isn't verified"
**Cause:** OAuth consent screen not verified by Google
**Fix:**
- For internal use: Set user type to "Internal"
- For public use: Submit for Google verification

---

## Security Notes

- Never commit `GOOGLE_CLIENT_SECRET` to git
- Use environment variables for all secrets
- Rotate secrets regularly
- Monitor OAuth usage in Google Cloud Console

---

## References

- Google OAuth Documentation: https://developers.google.com/identity/protocols/oauth2
- Google Cloud Console: https://console.cloud.google.com/apis/credentials
- Trinity OAuth Implementation: `src/backend/routers/credentials.py`
