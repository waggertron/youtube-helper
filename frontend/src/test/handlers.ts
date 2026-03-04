import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/health', () => HttpResponse.json({ status: 'ok', version: '0.1.0' })),
  http.get('/api/playlists', () => HttpResponse.json({ playlists: [] })),
  http.get('/api/watch-later', () => HttpResponse.json({ videos: [] })),
  http.get('/api/videos/liked', () => HttpResponse.json({ videos: [] })),
  http.get('/api/auth/status', () =>
    HttpResponse.json({ authenticated: false, has_client_secret: false, has_token: false })
  ),
  http.get('/api/queue', () => HttpResponse.json({ operations: [] })),
  http.get('/api/search', ({ request }) => {
    const url = new URL(request.url)
    return HttpResponse.json({ query: url.searchParams.get('q'), results: [] })
  }),
  http.post('/api/sync', () => HttpResponse.json({ operation_id: 1, message: 'Sync queued' })),
  http.post('/api/auth/upload-secret', () => HttpResponse.json({ message: 'Client secret saved' })),
  http.get('/api/auth/start', () =>
    HttpResponse.json({ auth_url: 'https://accounts.google.com/o/oauth2/auth?fake=1' })
  ),
]
