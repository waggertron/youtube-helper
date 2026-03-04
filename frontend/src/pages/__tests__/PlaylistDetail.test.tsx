import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
      }),
      http.post('/api/playlists/:id/like-all', () =>
        HttpResponse.json({ operation_id: 1, message: 'Like queued' }),
      ),
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

  it('shows confirm dialog with video title when remove is clicked', async () => {
    const user = userEvent.setup()
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('First Video')).toBeInTheDocument()
    })
    const removeButtons = screen.getAllByLabelText('Remove')
    await user.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByText('Remove Video')).toBeInTheDocument()
      expect(screen.getByText(/Remove "First Video" from "My Playlist"/)).toBeInTheDocument()
    })
  })

  it('does not call remove mutation until confirm is clicked', async () => {
    let removeCalled = false
    server.use(
      http.delete('/api/playlists/:playlistId/videos/:videoId', () => {
        removeCalled = true
        return HttpResponse.json({ message: 'removed' })
      }),
    )
    const user = userEvent.setup()
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('First Video')).toBeInTheDocument()
    })
    const removeButtons = screen.getAllByLabelText('Remove')
    await user.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByText('Remove Video')).toBeInTheDocument()
    })
    // Should not have called remove yet
    expect(removeCalled).toBe(false)
    // Now confirm
    await user.click(screen.getByText('Confirm'))
    await waitFor(() => expect(removeCalled).toBe(true))
  })

  it('cancels remove when cancel is clicked in confirm dialog', async () => {
    const user = userEvent.setup()
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('First Video')).toBeInTheDocument()
    })
    const removeButtons = screen.getAllByLabelText('Remove')
    await user.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByText('Remove Video')).toBeInTheDocument()
    })
    await user.click(screen.getByText('Cancel'))
    await waitFor(() => {
      expect(screen.queryByText('Remove Video')).not.toBeInTheDocument()
    })
  })

  it('renders Like All button', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('Like All')).toBeInTheDocument()
    })
  })

  it('shows liked status on videos', async () => {
    server.use(
      http.get('/api/playlists/:id/videos', () =>
        HttpResponse.json({
          playlist: { id: 'PL1', title: 'My Playlist', description: '', privacy_status: 'private', video_count: 2, source: 'api', last_synced: '' },
          videos: [
            { id: 'V1', title: 'First Video', channel_name: 'Channel A', channel_id: 'CA', duration: 300, watch_progress: 50, thumbnail_url: '', published_at: '', position: 0, is_liked: 1 },
            { id: 'V2', title: 'Second Video', channel_name: 'Channel B', channel_id: 'CB', duration: 180, watch_progress: 100, thumbnail_url: '', published_at: '', position: 1, is_liked: null },
          ],
        }),
      ),
    )
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByText('First Video')).toBeInTheDocument()
    })
    const likeButtons = screen.getAllByLabelText('Like')
    expect(likeButtons[0]).toBeDisabled()
    expect(likeButtons[1]).not.toBeDisabled()
  })

  it('renders view mode toggle', async () => {
    renderPlaylistDetail()
    await waitFor(() => {
      expect(screen.getByLabelText('Grid view')).toBeInTheDocument()
    })
  })
})
