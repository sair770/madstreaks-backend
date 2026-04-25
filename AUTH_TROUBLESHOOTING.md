# Authentication Troubleshooting Guide

## Current Issue
- ✅ Signup works (after updating .env to new Supabase project)
- ❌ Login fails with 400 Bad Request from Supabase auth endpoint

## Root Cause Analysis

The 400 error is coming from Supabase's `/auth/v1/token` endpoint, which means the auth provider settings might not be configured correctly in the **new** Supabase project.

## Step 1: Check Browser Console Error (First)

1. Open DevTools: `F12` or `Cmd+Option+I`
2. Go to **Console** tab
3. Try logging in with the account you just signed up
4. Look for detailed error message from Supabase client
5. **Share this error message** — it will tell us exactly what's wrong

Common error messages:
- `"Email not confirmed"` → Email verification is required
- `"Invalid login credentials"` → Email/password don't match
- `"Auth provider not enabled"` → Email/Password auth is disabled

## Step 2: Verify Supabase Email/Password Provider Settings

Go to your Supabase dashboard:

1. **URL:** https://supabase.com/dashboard
2. Select your project: `nnxkhnxroweehgzxflxm`
3. Go to: **Settings → Authentication → Providers**
4. Look for **Email** provider
5. Verify:
   - ✅ **Enabled** is checked
   - ✅ **Confirm email** is **DISABLED** (for development)
   - ✅ **Autoconfirm users** is **ENABLED** (for development)

### Screenshot reference:
```
Settings → Authentication → Providers → Email
├── [✓] Enable Email provider
├── [✓] Autoconfirm users  ← THIS MUST BE ON
├── [ ] Confirm email  ← THIS MUST BE OFF
└── [✓] Enable email OTP
```

**For development:** Enable "Autoconfirm users" so users don't need to verify email to log in.

## Step 3: Check Auth Settings

Still in **Settings → Authentication**:

1. Go to **Auth Settings** tab
2. Check **Site URL:** Should match your frontend domain
   - Development: `http://localhost:3000`
   - Production: `https://madstreaks.vercel.app`

3. Check **Redirect URLs:** Should include login redirect
   - Add: `http://localhost:3000/`
   - Add: `https://madstreaks.vercel.app/`

## Step 4: Test with Backend Endpoint (Fallback)

If frontend login still fails, test with the backend endpoint:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

Expected response:
```json
{
  "status": "success",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "test@example.com",
  "message": "Login successful"
}
```

If this works but frontend doesn't, the issue is in the frontend's Supabase client configuration.

## Step 5: Debug Supabase Client Configuration

Check that frontend `.env` is correct:

**File:** `/Users/sairam/madstreaks/.env`

```env
VITE_SUPABASE_URL=https://nnxkhnxroweehgzxflxm.supabase.co
VITE_SUPABASE_PROJECT_ID=nnxkhnxroweehgzxflxm
VITE_SUPABASE_PUBLISHABLE_KEY=sb_public_XXXX...  # From new project
```

**Don't use:**
- ❌ Old project URL: `nrppxfdspgsjuthahbju.supabase.co`
- ❌ Old publishable key

## Solution Checklist

- [ ] Check browser console error message
- [ ] Verify Email provider is **ENABLED** in Supabase
- [ ] Verify **Autoconfirm users** is **ON**
- [ ] Verify **Confirm email** is **OFF**
- [ ] Check Site URL and Redirect URLs are configured
- [ ] Verify frontend .env has correct new Supabase URL + publishable key
- [ ] Test with backend `/auth/login` endpoint
- [ ] Try logging in again in frontend

## If Still Failing

1. Take a screenshot of:
   - Browser DevTools Console (full error message)
   - Network tab → POST /auth/v1/token → Response body
   - Supabase Dashboard → Settings → Authentication → Email provider settings

2. Share these screenshots so we can diagnose further

## Additional Notes

**Current Architecture:**
- Frontend calls Supabase auth directly (not through backend)
- This is standard for SPA + Supabase pattern
- Backend validates the session token for API requests

**Backend Auth Endpoints Available:**
- `POST /auth/login` — Backend login (for fallback/testing)
- `POST /auth/signup` — Backend signup (for fallback/testing)
- `GET /auth/debug` — Debug endpoint to verify Supabase connectivity

These backend endpoints are useful for debugging but the frontend typically uses Supabase directly.
