# External Public URL for Public Agent Links

> **Requirement ID**: PUB-002
> **Status**: ✅ Implemented
> **Priority**: Medium
> **Requested By**: Eugene
> **Date**: 2026-02-16
> **Implemented**: 2026-02-16

---

## Summary

Add support for an external (internet-accessible) URL for public agent links, separate from the internal VPN URL. This enables sharing public chat links with external users who are not on the Tailscale VPN.

## Background

Trinity runs on GCP behind a Tailscale VPN. The existing Public Agent Links feature (PUB-001, implemented 2025-12-22) generates shareable URLs, but these URLs only work for users on the VPN.

**Current behavior:**
- Public link URL: `https://trinity.abilityai.dev/chat/{token}` (internal only)
- External users cannot access this URL

**Desired behavior:**
- Internal URL: `https://trinity.abilityai.dev/chat/{token}` (VPN users)
- External URL: `https://public.abilityai.dev/chat/{token}` (anyone on internet)
- Owner can copy either URL depending on who they're sharing with

## Use Cases

1. **Share with client (external)**: Agent owner creates public link, copies external URL, sends to client who is not on VPN
2. **Share with teammate (internal)**: Agent owner copies internal URL for someone on the VPN
3. **Demo to prospect**: Quick external link for product demos

---

## Functional Requirements

### FR-1: External URL Configuration

Add a new environment variable `PUBLIC_CHAT_URL` that specifies the external URL base.

**Environment Variable:**
```bash
# External URL for public chat links (optional)
# When set, enables "Copy External Link" button in UI
PUBLIC_CHAT_URL=https://public.abilityai.dev
```

**Behavior:**
- If not set: External URL feature is disabled (current behavior)
- If set: External URL is available alongside internal URL

### FR-2: Backend API Changes

**File: `src/backend/config.py`**

Add new configuration constant:
```python
# External Public URL (for sharing outside VPN)
# When set, public links will include both internal and external URLs
PUBLIC_CHAT_URL = os.getenv("PUBLIC_CHAT_URL", "")
```

**File: `src/backend/routers/public_links.py`**

Modify `_link_to_response()` to include external URL:
```python
def _link_to_response(link: dict, include_usage: bool = True) -> PublicLinkWithUrl:
    """Convert a database link dict to response model with URL."""
    usage_stats = None
    if include_usage:
        usage_stats = db.get_public_link_usage_stats(link["id"])

    # Build URLs
    internal_url = f"{FRONTEND_URL}/chat/{link['token']}"
    external_url = f"{PUBLIC_CHAT_URL}/chat/{link['token']}" if PUBLIC_CHAT_URL else None

    return PublicLinkWithUrl(
        # ... existing fields ...
        url=internal_url,
        external_url=external_url,  # NEW FIELD
        # ...
    )
```

**File: `src/backend/db_models.py`**

Update `PublicLinkWithUrl` model to include external URL:
```python
class PublicLinkWithUrl(PublicLink):
    """Public link with generated URL."""
    url: str  # Internal URL (existing)
    external_url: Optional[str] = None  # External URL (NEW)
    usage_stats: Optional[dict] = None
```

### FR-3: Frontend UI Changes

**File: `src/frontend/src/components/PublicLinksPanel.vue`**

Add "Copy External Link" button when external URL is available.

**Changes to link list item (around line 79-92):**
```vue
<!-- URL preview -->
<div class="mt-2 flex items-center space-x-2">
  <code class="flex-1 text-xs text-gray-500 ...">
    {{ link.url }}
  </code>
  <button @click="copyLink(link, 'internal')" title="Copy internal link">
    <!-- existing copy icon -->
  </button>
  <!-- NEW: External link button -->
  <button
    v-if="link.external_url"
    @click="copyLink(link, 'external')"
    class="p-1.5 text-gray-400 hover:text-green-600 ..."
    title="Copy external link (public internet)"
  >
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
    </svg>
  </button>
</div>
```

**Update `copyLink()` method (around line 452):**
```javascript
const copyLink = async (link, type = 'internal') => {
  try {
    const url = type === 'external' && link.external_url
      ? link.external_url
      : link.url
    await navigator.clipboard.writeText(url)
    copyNotification.value = type === 'external'
      ? 'External link copied!'
      : 'Link copied to clipboard!'
    setTimeout(() => {
      copyNotification.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy link:', err)
  }
}
```

**Add visual indicator for external URL availability:**
- Show a small "External" badge or globe icon next to links that have external URLs
- Tooltip explaining the difference between internal and external links

### FR-4: Settings Page Display (Optional)

**File: `src/frontend/src/views/Settings.vue`**

Display the external URL configuration status in Settings page (read-only, informational):

```vue
<!-- Public Access Configuration -->
<div class="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg">
  <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">External Public Access</h3>
  <div v-if="publicChatUrl" class="mt-2">
    <span class="text-green-600 dark:text-green-400">✓ Configured</span>
    <code class="ml-2 text-xs">{{ publicChatUrl }}</code>
  </div>
  <div v-else class="mt-2 text-gray-500 dark:text-gray-400">
    Not configured. Set PUBLIC_CHAT_URL environment variable to enable.
  </div>
</div>
```

**Backend endpoint for settings info:**

Add `PUBLIC_CHAT_URL` to the existing `/api/settings` or `/api/health` response so frontend knows if it's configured.

---

## Non-Functional Requirements

### NFR-1: Backward Compatibility

- If `PUBLIC_CHAT_URL` is not set, behavior is identical to current implementation
- No database migrations required
- No breaking changes to existing API contracts

### NFR-2: Security

- External URL does not bypass any existing security (rate limiting, email verification)
- Token security remains the same (192-bit random, unguessable)
- No additional authentication required for external access (same as internal public links)

---

## Implementation Plan

### Phase 1: Backend (30 minutes)

1. Add `PUBLIC_CHAT_URL` to `config.py`
2. Add `external_url` field to `PublicLinkWithUrl` model in `db_models.py`
3. Update `_link_to_response()` in `public_links.py` to include external URL
4. Add `public_chat_url` to health/settings endpoint response

### Phase 2: Frontend (30 minutes)

1. Update `PublicLinksPanel.vue`:
   - Add external link copy button with globe icon
   - Update `copyLink()` to handle both URL types
   - Update notification message
2. Optional: Add status display to Settings page

### Phase 3: Documentation (15 minutes)

1. Update `docs/memory/feature-flows/public-agent-links.md`
2. Update `docs/DEPLOYMENT.md` with `PUBLIC_CHAT_URL` documentation
3. Update `.env.example` with new variable

---

## Files to Modify

| File | Change |
|------|--------|
| `src/backend/config.py` | Add `PUBLIC_CHAT_URL` constant |
| `src/backend/db_models.py` | Add `external_url` field to `PublicLinkWithUrl` |
| `src/backend/routers/public_links.py` | Update `_link_to_response()` |
| `src/frontend/src/components/PublicLinksPanel.vue` | Add external link button, update copyLink() |
| `.env.example` | Add `PUBLIC_CHAT_URL` documentation |
| `docs/memory/feature-flows/public-agent-links.md` | Update with external URL feature |
| `docs/DEPLOYMENT.md` | Add configuration documentation |

---

## Testing

### Test Cases

| # | Test | Expected Result |
|---|------|-----------------|
| 1 | `PUBLIC_CHAT_URL` not set | No external_url in API response, no external button in UI |
| 2 | `PUBLIC_CHAT_URL` set | external_url in API response, external button visible |
| 3 | Copy internal link | Copies internal URL to clipboard |
| 4 | Copy external link | Copies external URL to clipboard |
| 5 | Create new link with external configured | Both URLs returned in response |
| 6 | List links with external configured | All links have both URLs |

### Manual Testing Steps

1. Start backend without `PUBLIC_CHAT_URL` - verify current behavior unchanged
2. Set `PUBLIC_CHAT_URL=https://test.example.com` and restart
3. Create a public link
4. Verify API response includes `external_url`
5. Verify UI shows external link button
6. Copy external link, verify correct URL copied
7. Access external URL (requires infra setup) - verify chat works

---

## Dependencies

### Infrastructure (Separate Task)

This requirement assumes infrastructure is configured separately (see `PUBLIC_EXTERNAL_ACCESS_SETUP.md`):
- Tailscale Funnel, OR
- GCP Load Balancer, OR
- Cloudflare Tunnel

The code changes work regardless of which infrastructure option is chosen.

---

## Related Documents

- `docs/requirements/PUBLIC_EXTERNAL_ACCESS_SETUP.md` - Infrastructure setup guide
- `docs/memory/feature-flows/public-agent-links.md` - Existing feature flow
- `docs/memory/requirements.md` - Section 15.1 Public Agent Links

---

## Acceptance Criteria

- [x] `PUBLIC_CHAT_URL` environment variable is recognized by backend
- [x] API returns `external_url` field when configured
- [x] UI shows "Copy External Link" button when external URL available
- [x] Clicking external link button copies correct URL
- [x] No changes to behavior when `PUBLIC_CHAT_URL` is not set
- [x] Documentation updated
- [x] `.env.example` updated
