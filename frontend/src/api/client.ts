const BASE = '/api'
const isDev = import.meta.env.DEV

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  if (isDev) console.debug('[api]', options?.method || 'GET', path)
  const { headers, ...rest } = options ?? {}
  const resp = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    if (isDev) console.error('[api] Error:', path, err.detail)
    throw new Error(err.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export interface TaskStatus {
  status: string
  progress: number
  message: string
  error: string | null
  removed?: number
  total?: number
}

export const api = {
  // Health
  health: () => request<{ status: string; version: string }>('/health'),

  // Auth
  authStatus: () =>
    request<{
      authenticated: boolean
      has_client_secret: boolean
      has_token: boolean
    }>('/auth/status'),
  uploadSecret: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/auth/upload-secret`, { method: 'POST', body: form })
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail || 'Upload failed') })
        return r.json()
      })
  },
  startAuth: () => request<{ auth_url: string }>('/auth/start'),

  // Playlists
  listPlaylists: () => request<{ playlists: Playlist[] }>('/playlists'),
  getPlaylistVideos: (id: string) =>
    request<{ playlist: Playlist; videos: Video[] }>(
      `/playlists/${id}/videos`,
    ),
  createPlaylist: (data: { title: string; privacy?: string }) =>
    request<{ id: string; title: string }>('/playlists', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deletePlaylist: (id: string) =>
    request<{ deleted: string }>(`/playlists/${id}`, { method: 'DELETE' }),
  addVideos: (playlistId: string, videoIds: string[]) =>
    request<{ added: number }>(`/playlists/${playlistId}/videos`, {
      method: 'POST',
      body: JSON.stringify({ video_ids: videoIds }),
    }),
  removeVideo: (playlistId: string, videoId: string) =>
    request<{ removed: string }>(`/playlists/${playlistId}/videos/${videoId}`, {
      method: 'DELETE',
    }),
  reorderPlaylist: (playlistId: string, videoIds: string[]) =>
    request<{ reordered: boolean }>(`/playlists/${playlistId}/reorder`, {
      method: 'PUT',
      body: JSON.stringify({ video_ids: videoIds }),
    }),
  likeAllPlaylist: (playlistId: string) =>
    request<Record<string, unknown>>(`/playlists/${playlistId}/like-all`, { method: 'POST' }),

  // Videos
  likedVideos: () => request<{ videos: Video[] }>('/videos/liked'),
  likeVideo: (id: string) =>
    request<{ video_id: string; status: string }>(`/videos/${id}/like`, { method: 'POST' }),
  unlikeVideo: (id: string) =>
    request<{ video_id: string; status: string }>(`/videos/${id}/like`, { method: 'DELETE' }),
  listAllVideos: () => request<{ videos: VideoWithPlaylists[] }>('/videos'),

  // Watch Later
  watchLater: () => request<{ videos: Video[] }>('/watch-later'),
  watchLaterWatched: (threshold: number) =>
    request<{ videos: Video[] }>(
      `/watch-later/watched?threshold=${threshold}`,
    ),
  watchLaterUnwatched: (threshold: number) =>
    request<{ videos: Video[] }>(
      `/watch-later/unwatched?threshold=${threshold}`,
    ),
  importWatchLater: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/watch-later/import`, { method: 'POST', body: form })
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail || 'Import failed') })
        return r.json() as Promise<{ imported: number; total_parsed: number }>
      })
  },
  exportWatchLater: (data: { target: string; threshold: number }) =>
    request<{ exported: number; playlist_id: string }>('/watch-later/export', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  purgeWatchLater: (data: { threshold: number }) =>
    request<{ status: string; message: string; total: number }>('/watch-later/purge', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Search
  search: (q: string, threshold?: number) =>
    request<{ query: string; results: SearchResult[] }>(
      `/search?q=${encodeURIComponent(q)}${threshold ? `&threshold=${threshold}` : ''}`,
    ),

  // System
  resetDatabase: () => request<{ message: string }>('/reset', { method: 'POST' }),

  // Sync
  sync: () => request<{ status: string; message: string }>('/sync', { method: 'POST' }),
  syncStatus: () => request<TaskStatus>('/sync/status'),

  // Purge status
  purgeStatus: () => request<TaskStatus>('/watch-later/purge/status'),
}

// Types
export interface Playlist {
  id: string
  title: string
  description: string
  privacy_status: string
  video_count: number
  source: string
  last_synced: string
}

export interface Video {
  id: string
  title: string
  channel_name: string
  channel_id: string
  duration: number
  watch_progress: number
  thumbnail_url: string
  published_at: string
  position?: number
  is_liked?: number | null
}

export interface VideoWithPlaylists extends Video {
  playlist_names: string | null
  playlist_ids: string | null
}

export interface SearchResult extends Partial<Video>, Partial<Playlist> {
  type: 'video' | 'playlist'
  score: number
}
