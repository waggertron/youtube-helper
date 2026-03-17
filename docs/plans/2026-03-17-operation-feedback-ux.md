# Operation Feedback UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give users clear feedback when slow operations (sync, purge, import, export) are running, complete, or fail — via toast notifications and inline progress indicators.

**Architecture:** Toast notifications (via existing `useToast`) fire on operation start/complete/fail from any page. Inline progress bars show on the triggering page while an operation is running. Uses existing `useSyncStatus`/`usePurgeStatus` polling hooks and MUI `LinearProgress` + `Alert` components.

**Tech Stack:** React, MUI (LinearProgress, Alert, Snackbar), React Query, existing ToastProvider

**Design doc:** `docs/plans/2026-03-17-simplify-remove-queue-design.md`

---

### Task 1: Create OperationStatus Component

A reusable inline component that shows progress for a background operation. Displays a card with progress bar, status message, and completion/error state.

**Files:**
- Create: `frontend/src/components/OperationStatus.tsx`
- Create: `frontend/src/components/__tests__/OperationStatus.test.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/src/components/__tests__/OperationStatus.test.tsx
import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../test/render'
import OperationStatus from '../OperationStatus'

describe('OperationStatus', () => {
  it('renders nothing when status is idle', () => {
    const { container } = renderWithProviders(
      <OperationStatus status={{ status: 'idle', progress: 0, message: '', error: null }} label="Sync" />
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows progress bar and message when running', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'running', progress: 50, message: 'Syncing playlists...', error: null }}
        label="Sync"
      />
    )
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.getByText('Syncing playlists...')).toBeInTheDocument()
  })

  it('shows success alert when completed', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'completed', progress: 100, message: 'Synced 12 playlists', error: null }}
        label="Sync"
      />
    )
    expect(screen.getByText(/Sync complete/i)).toBeInTheDocument()
    expect(screen.getByText('Synced 12 playlists')).toBeInTheDocument()
  })

  it('shows error alert when failed', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'failed', progress: 30, message: '', error: 'Network error' }}
        label="Sync"
      />
    )
    expect(screen.getByText(/Sync failed/i)).toBeInTheDocument()
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/components/__tests__/OperationStatus.test.tsx`
Expected: FAIL — module not found

**Step 3: Write implementation**

```tsx
// frontend/src/components/OperationStatus.tsx
import { Alert, Box, LinearProgress, Typography } from '@mui/material'
import type { TaskStatus } from '../api/client'

interface Props {
  status: TaskStatus | null | undefined
  label: string
}

export default function OperationStatus({ status, label }: Props) {
  if (!status || status.status === 'idle') return null

  if (status.status === 'running') {
    return (
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            {status.message || `${label} in progress...`}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {status.progress}%
          </Typography>
        </Box>
        <LinearProgress variant="determinate" value={status.progress} />
      </Box>
    )
  }

  if (status.status === 'completed') {
    return (
      <Alert severity="success" sx={{ mb: 2 }}>
        <strong>{label} complete.</strong> {status.message}
      </Alert>
    )
  }

  if (status.status === 'failed') {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        <strong>{label} failed.</strong> {status.error}
      </Alert>
    )
  }

  return null
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/components/__tests__/OperationStatus.test.tsx`
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
git add frontend/src/components/OperationStatus.tsx frontend/src/components/__tests__/OperationStatus.test.tsx
git commit -m "feat: add OperationStatus inline progress component"
```

---

### Task 2: Add Toast Notifications to Mutations

Wire `useToast()` into the mutation hooks so every operation shows a toast on start, success, and failure. This gives feedback from any page.

**Files:**
- Modify: `frontend/src/hooks/useApi.ts`
- Modify: `frontend/src/hooks/__tests__/useApi.test.tsx`

**Step 1: Write the failing test**

```tsx
// Add to frontend/src/hooks/__tests__/useApi.test.tsx
// Test that useSync shows toast on success
import { renderHook, waitFor } from '@testing-library/react'

describe('useSync toast', () => {
  it('calls toast.info on mutate and toast.success on success', async () => {
    // This test verifies the hook calls toast methods
    // Implementation uses onMutate for "started" toast and onSuccess for "complete" toast
  })
})
```

Note: Testing toasts through hooks is tricky with React Query. The primary testing will be done via the page-level tests in Task 3 and 4. For this task, focus on the implementation and verify manually that existing tests still pass.

**Step 2: Update useApi.ts**

The key change: mutation hooks need access to `useToast()`. But hooks can't be called conditionally. The cleanest approach is to add toast calls in the `onMutate`, `onSuccess`, and `onError` callbacks of each mutation.

However, `useToast()` requires being inside a `ToastProvider`. The mutation hooks are used inside components which are wrapped in `ToastProvider` (via the render tree). But the hooks themselves are plain hooks — they can call `useToast()` internally.

Update each mutation hook to accept an optional toast parameter, or better: create a helper that wraps mutations with toast behavior.

```typescript
// Add to frontend/src/hooks/useApi.ts

// Import useToast at the top
import { useToast } from '../components/ToastProvider'

// Update useSync:
export const useSync = () => {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: api.sync,
    onMutate: () => toast.info('Sync started...'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-status'] })
      qc.invalidateQueries({ queryKey: ['playlists'] })
      // Don't toast here — the status polling + OperationStatus handles completion
    },
    onError: (err: Error) => toast.error(`Sync failed: ${err.message}`),
  })
}

// Update useExportWL:
export const useExportWL = () => {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: api.exportWatchLater,
    onMutate: () => toast.info('Exporting Watch Later videos...'),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['watch-later'] })
      toast.success(`Export complete: ${data.exported} videos exported`)
    },
    onError: (err: Error) => toast.error(`Export failed: ${err.message}`),
  })
}

// Update usePurgeWL:
export const usePurgeWL = () => {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: api.purgeWatchLater,
    onMutate: () => toast.info('Purge started — Chrome will open shortly...'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purge-status'] })
      qc.invalidateQueries({ queryKey: ['watch-later'] })
    },
    onError: (err: Error) => toast.error(`Purge failed: ${err.message}`),
  })
}

// Update useImportWatchLater:
export function useImportWatchLater() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (file: File) => api.importWatchLater(file),
    onMutate: () => toast.info('Importing Watch Later videos...'),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['watch-later'] })
      toast.success(`Imported ${data.imported} videos`)
    },
    onError: (err: Error) => toast.error(`Import failed: ${err.message}`),
  })
}

// Update useLikeAll:
export function useLikeAll() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: (playlistId: string) => api.likeAllPlaylist(playlistId),
    onMutate: () => toast.info('Liking all videos...'),
    onSuccess: (_data, playlistId) => {
      qc.invalidateQueries({ queryKey: ['liked-videos'] })
      qc.invalidateQueries({ queryKey: ['playlist', playlistId] })
      toast.success('All videos liked')
    },
    onError: (err: Error) => toast.error(`Like all failed: ${err.message}`),
  })
}

// Update useResetDatabase:
export function useResetDatabase() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: () => api.resetDatabase(),
    onSuccess: () => {
      qc.invalidateQueries()
      toast.success('Database reset')
    },
    onError: (err: Error) => toast.error(`Reset failed: ${err.message}`),
  })
}
```

**Step 3: Update test helpers**

The hooks now call `useToast()` which requires `ToastProvider`. The `renderWithProviders` helper in `frontend/src/test/render.tsx` already wraps with `ToastProvider`, so renderHook tests need to use this wrapper too.

Check if existing tests pass — they should since the test render wrapper includes `ToastProvider`.

**Step 4: Run tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add frontend/src/hooks/useApi.ts
git commit -m "feat: add toast notifications to all mutation hooks"
```

---

### Task 3: Add Inline Sync Progress to Dashboard

Show sync progress inline on the Dashboard page, and toast when sync completes.

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/__tests__/Dashboard.test.tsx`

**Step 1: Write the failing test**

```tsx
// Add to frontend/src/pages/__tests__/Dashboard.test.tsx
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'

it('shows sync progress when sync is running', async () => {
  server.use(
    http.get('/api/sync/status', () =>
      HttpResponse.json({ status: 'running', progress: 50, message: 'Syncing playlists...', error: null })
    ),
  )
  renderWithProviders(<Dashboard />)
  await waitFor(() => {
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.getByText('Syncing playlists...')).toBeInTheDocument()
  })
})

it('shows sync completion message', async () => {
  server.use(
    http.get('/api/sync/status', () =>
      HttpResponse.json({ status: 'completed', progress: 100, message: 'Synced 12 playlists, 340 videos', error: null })
    ),
  )
  renderWithProviders(<Dashboard />)
  await waitFor(() => {
    expect(screen.getByText(/Sync complete/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/pages/__tests__/Dashboard.test.tsx`
Expected: FAIL — no progressbar rendered

**Step 3: Update Dashboard.tsx**

```tsx
// Add imports:
import { useSyncStatus } from '../hooks/useApi'
import OperationStatus from '../components/OperationStatus'

// Inside Dashboard component, after useSync():
const { data: syncStatus } = useSyncStatus()

// In JSX, after the Quick Actions section:
<OperationStatus status={syncStatus} label="Sync" />
```

Add a default MSW handler for `/api/sync/status`:

```typescript
// Add to frontend/src/test/handlers.ts:
http.get('/api/sync/status', () => HttpResponse.json({ status: 'idle', progress: 0, message: '', error: null })),
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/pages/__tests__/Dashboard.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/__tests__/Dashboard.test.tsx frontend/src/test/handlers.ts
git commit -m "feat: show sync progress inline on Dashboard"
```

---

### Task 4: Add Inline Purge Progress to Watch Later Page

Show purge progress on the Watch Later page while Playwright is removing videos.

**Files:**
- Modify: `frontend/src/pages/WatchLater.tsx`
- Modify: `frontend/src/pages/__tests__/WatchLater.test.tsx`

**Step 1: Write the failing test**

```tsx
// Add to frontend/src/pages/__tests__/WatchLater.test.tsx
it('shows purge progress when purge is running', async () => {
  server.use(
    http.get('/api/watch-later/purge/status', () =>
      HttpResponse.json({ status: 'running', progress: 40, message: 'Removed 4/10', error: null, removed: 4, total: 10 })
    ),
  )
  renderWithProviders(<WatchLater />)
  await waitFor(() => {
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.getByText('Removed 4/10')).toBeInTheDocument()
  })
})

it('shows purge completion', async () => {
  server.use(
    http.get('/api/watch-later/purge/status', () =>
      HttpResponse.json({ status: 'completed', progress: 100, message: 'Removed 10 videos', error: null })
    ),
  )
  renderWithProviders(<WatchLater />)
  await waitFor(() => {
    expect(screen.getByText(/Purge complete/i)).toBeInTheDocument()
  })
})
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/pages/__tests__/WatchLater.test.tsx`
Expected: FAIL

**Step 3: Update WatchLater.tsx**

```tsx
// Add imports:
import { usePurgeStatus } from '../hooks/useApi'
import OperationStatus from '../components/OperationStatus'

// Inside component:
const { data: purgeStatus } = usePurgeStatus()

// In JSX, after the button row and before the threshold slider:
<OperationStatus status={purgeStatus} label="Purge" />
```

Add default MSW handler:

```typescript
// Add to frontend/src/test/handlers.ts:
http.get('/api/watch-later/purge/status', () => HttpResponse.json({ status: 'idle', progress: 0, message: '', error: null })),
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/pages/__tests__/WatchLater.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/WatchLater.tsx frontend/src/pages/__tests__/WatchLater.test.tsx frontend/src/test/handlers.ts
git commit -m "feat: show purge progress inline on Watch Later page"
```

---

### Task 5: Auto-Dismiss Completed Status After Delay

The OperationStatus component should auto-dismiss completed/failed status after a few seconds so it doesn't stay permanently on screen.

**Files:**
- Modify: `frontend/src/components/OperationStatus.tsx`
- Modify: `frontend/src/components/__tests__/OperationStatus.test.tsx`

**Step 1: Write the failing test**

```tsx
// Add to OperationStatus.test.tsx
import { act } from '@testing-library/react'
import { vi } from 'vitest'

it('auto-dismisses completed status after 8 seconds', async () => {
  vi.useFakeTimers()

  const { container, rerender } = renderWithProviders(
    <OperationStatus
      status={{ status: 'completed', progress: 100, message: 'Done', error: null }}
      label="Sync"
    />
  )
  expect(screen.getByText(/Sync complete/i)).toBeInTheDocument()

  act(() => { vi.advanceTimersByTime(8000) })

  // After 8s, should be dismissed
  rerender(
    // Need to wrap in providers again if using rerender directly
    // Alternative: check that the component renders null after timeout
  )

  vi.useRealTimers()
})
```

Note: Auto-dismiss is best handled with internal state. When status transitions to completed/failed, start a timer. When it fires, set an internal `dismissed` flag. If status changes back to running, clear the flag.

**Step 2: Implement auto-dismiss**

Update `OperationStatus.tsx`:

```tsx
import { useEffect, useState } from 'react'

export default function OperationStatus({ status, label }: Props) {
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'failed') {
      const timer = setTimeout(() => setDismissed(true), 8000)
      return () => clearTimeout(timer)
    }
    setDismissed(false)
  }, [status?.status])

  if (!status || status.status === 'idle' || dismissed) return null

  // ... rest unchanged
}
```

**Step 3: Run tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run src/components/__tests__/OperationStatus.test.tsx`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/components/OperationStatus.tsx frontend/src/components/__tests__/OperationStatus.test.tsx
git commit -m "feat: auto-dismiss completed/failed operation status after 8s"
```

---

### Task 6: Disable Buttons During Active Operations

When an operation is running, the triggering button should be disabled and show a loading indicator.

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/WatchLater.tsx`

**Step 1: Update Dashboard sync button**

The sync button already uses `syncMutation.isPending` but that only covers the initial POST. After the POST returns (immediately, since it's a 202), `isPending` is false even though sync is still running.

Fix: also disable when `syncStatus?.status === 'running'`.

```tsx
// In Dashboard.tsx:
<Button
  variant="contained"
  startIcon={syncStatus?.status === 'running' ? <CircularProgress size={20} color="inherit" /> : <Sync />}
  onClick={() => syncMutation.mutate()}
  disabled={syncMutation.isPending || syncStatus?.status === 'running'}
>
  {syncStatus?.status === 'running' ? 'Syncing...' : 'Sync Playlists'}
</Button>
```

Import `CircularProgress` from MUI.

**Step 2: Update Watch Later purge button**

```tsx
// In WatchLater.tsx:
<Button
  variant="contained"
  color="warning"
  onClick={() => setConfirmPurge(true)}
  disabled={purgeWL.isPending || purgeStatus?.status === 'running'}
>
  {purgeStatus?.status === 'running' ? 'Purging...' : 'Purge'}
</Button>
```

**Step 3: Run all frontend tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx frontend/src/pages/WatchLater.tsx
git commit -m "feat: disable buttons and show loading during active operations"
```

---

### Task 7: Toast on Background Task Completion via Status Polling

When sync or purge completes (detected by status polling), fire a toast. This ensures the user sees the result even if they navigated away from the triggering page.

**Files:**
- Modify: `frontend/src/hooks/useApi.ts`

**Step 1: Update useSyncStatus and usePurgeStatus**

Add `onSuccess` callbacks that detect transitions to completed/failed and fire toasts. Use a ref to track the previous status.

Actually, the cleaner approach: create wrapper hooks that combine the status polling with toast side-effects.

```typescript
// Add to useApi.ts:
import { useEffect, useRef } from 'react'

export function useSyncStatusWithToast() {
  const query = useSyncStatus()
  const toast = useToast()
  const prevStatus = useRef<string | undefined>()

  useEffect(() => {
    const current = query.data?.status
    const prev = prevStatus.current
    if (prev === 'running' && current === 'completed') {
      toast.success(`Sync complete: ${query.data?.message || ''}`)
    } else if (prev === 'running' && current === 'failed') {
      toast.error(`Sync failed: ${query.data?.error || 'Unknown error'}`)
    }
    prevStatus.current = current
  }, [query.data?.status])

  return query
}

export function usePurgeStatusWithToast() {
  const query = usePurgeStatus()
  const toast = useToast()
  const prevStatus = useRef<string | undefined>()

  useEffect(() => {
    const current = query.data?.status
    const prev = prevStatus.current
    if (prev === 'running' && current === 'completed') {
      toast.success(`Purge complete: ${query.data?.message || ''}`)
    } else if (prev === 'running' && current === 'failed') {
      toast.error(`Purge failed: ${query.data?.error || 'Unknown error'}`)
    }
    prevStatus.current = current
  }, [query.data?.status])

  return query
}
```

**Step 2: Update Dashboard and WatchLater to use the toast-enabled versions**

In `Dashboard.tsx`: change `useSyncStatus()` to `useSyncStatusWithToast()`
In `WatchLater.tsx`: change `usePurgeStatus()` to `usePurgeStatusWithToast()`

**Step 3: Run all tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add frontend/src/hooks/useApi.ts frontend/src/pages/Dashboard.tsx frontend/src/pages/WatchLater.tsx
git commit -m "feat: toast notifications when background operations complete"
```

---

### Task 8: Final Test Run

Verify everything works end-to-end.

**Step 1: Run all frontend tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper/frontend && npx vitest run`
Expected: ALL PASS

**Step 2: Run all backend tests**

Run: `cd /Users/weylinwagnon/coding/fam/youtube-helper && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "chore: final cleanup for operation feedback UX"
```
