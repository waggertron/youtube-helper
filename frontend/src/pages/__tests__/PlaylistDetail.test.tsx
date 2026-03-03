import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'
import { Routes, Route } from 'react-router-dom'
import PlaylistDetail from '../PlaylistDetail'

function renderPlaylistDetail(id = 'PL1') {
  return renderWithProviders(
    <Routes>
      <Route path="/playlists/:id" element={<PlaylistDetail />} />
    </Routes>,
    `/playlists/${id}`
  )
}

describe('PlaylistDetail', () => {
  beforeEach(() => {
    server.use(
      http.get('/api/playlists/:id/videos', ({ params }) => {
        if (params.id === 'PL1') {
          return HttpResponse.json({
            playlist: { id: 'PL1', title: 'My Playlist', description: '', privacy_status: 'private', video_count: 2, source: 'api', last_synced: '' },
            videos: [
              { id: 'V1', title: 'First Video', channel_name: 'Channel A', channel_id: 'CA', duration: 300, watch_progress: 50, thumbnail_url: '', published_at: '', position: 0 },
              { id: 'V2', title: 'Second Video', channel_name: 'Channel B', channel_id: 'CB', duration: 180, watch_progress: 100, thumbnail_url: '', published_at: '', position: 1 },
            ],
          })
        }
        return HttpResponse.json({ playlist: null, videos: [] }, { status: 404 })
      })
    )
  })

  it('renders playlist title', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('My Playlist')).toBeInTheDocument()
    })
  })

  it('renders video table with videos', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('First Video')).toBeInTheDocument()
      expect(screen.getByText('Second Video')).toBeInTheDocument()
    })
  })

  it('renders back button', () => {
    renderPlaylistDetail()
    expect(screen.getByLabelText('Back to playlists')).toBeInTheDocument()
  })

  it('shows channel names in video table', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('Channel A')).toBeInTheDocument()
      expect(screen.getByText('Channel B')).toBeInTheDocument()
    })
  })

  it('shows remove buttons for videos', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getAllByLabelText('Remove')).toHaveLength(2)
    })
  })

  it('shows like buttons for videos', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getAllByLabelText('Like')).toHaveLength(2)
    })
  })
})
