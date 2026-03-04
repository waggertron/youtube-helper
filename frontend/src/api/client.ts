const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers, ...rest } = options ?? {}
  const resp = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
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
    request<QueuedOp>('/playlists', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deletePlaylist: (id: string) =>
    request<QueuedOp>(`/playlists/${id}`, { method: 'DELETE' }),
  addVideos: (playlistId: string, videoIds: string[]) =>
    request<QueuedOp>(`/playlists/${playlistId}/videos`, {
      method: 'POST',
      body: JSON.stringify({ video_ids: videoIds }),
    }),
  removeVideo: (playlistId: string, videoId: string) =>
    request<QueuedOp>(`/playlists/${playlistId}/videos/${videoId}`, {
      method: 'DELETE',
    }),
  reorderPlaylist: (playlistId: string, videoIds: string[]) =>
    request<QueuedOp>(`/playlists/${playlistId}/reorder`, {
      method: 'PUT',
      body: JSON.stringify({ video_ids: videoIds }),
    }),
  likeAllPlaylist: (playlistId: string) =>
    request<QueuedOp>(`/playlists/${playlistId}/like-all`, { method: 'POST' }),

  // Videos
  likedVideos: () => request<{ videos: Video[] }>('/videos/liked'),
  likeVideo: (id: string) =>
    request<QueuedOp>(`/videos/${id}/like`, { method: 'POST' }),
  unlikeVideo: (id: string) =>
    request<QueuedOp>(`/videos/${id}/like`, { method: 'DELETE' }),
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
  scrapeWatchLater: () =>
    request<QueuedOp>('/watch-later/scrape', { method: 'POST' }),
  exportWatchLater: (data: { target: string; threshold: number }) =>
    request<QueuedOp>('/watch-later/export', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  purgeWatchLater: (data: { threshold: number }) =>
    request<QueuedOp>('/watch-later/purge', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  pruneExports: () =>
    request<QueuedOp>('/watch-later/prune-exports', { method: 'POST' }),

  // Search
  search: (q: string, threshold?: number) =>
    request<{ query: string; results: SearchResult[] }>(
      `/search?q=${encodeURIComponent(q)}${threshold ? `&threshold=${threshold}` : ''}`,
    ),

  // System
  resetDatabase: () => request<{ message: string }>('/reset', { method: 'POST' }),

  // Sync
  sync: () => request<QueuedOp>('/sync', { method: 'POST' }),

  // Queue
  listQueue: () => request<{ operations: QueueOp[] }>('/queue'),
  cancelOp: (id: number) =>
    request<{ message: string }>(`/queue/${id}`, { method: 'DELETE' }),
  retryOp: (id: number) =>
    request<{ message: string }>(`/queue/${id}/retry`, { method: 'POST' }),
  skipOp: (id: number) =>
    request<{ message: string }>(`/queue/${id}/skip`, { method: 'POST' }),
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

export interface QueueOp {
  id: number
  type: string
  params: string
  status: string
  progress: number
  message: string
  error: string
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface QueuedOp {
  operation_id: number
  message: string
}
