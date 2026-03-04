import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'
import { Routes, Route } from 'react-router-dom'
import Playlists from '../Playlists'

function renderPlaylists() {
  return renderWithProviders(
    <Routes>
      <Route path="/playlists" element={<Playlists />} />
    </Routes>,
    '/playlists'
  )
}

describe('Playlists', () => {
  it('renders the page heading', () => {
    renderPlaylists()
    expect(screen.getByText('Playlists')).toBeInTheDocument()
  })

  it('shows create playlist button', () => {
    renderPlaylists()
    expect(screen.getByText('Create Playlist')).toBeInTheDocument()
  })

  it('displays playlists from API', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({
          playlists: [
            { id: 'PL1', title: 'My Playlist', video_count: 5, privacy_status: 'private', description: '', source: 'api', last_synced: '' },
            { id: 'PL2', title: 'Another Playlist', video_count: 12, privacy_status: 'public', description: '', source: 'api', last_synced: '' },
          ],
        })
      ),
    )
    renderPlaylists()
    await waitFor(() => {
      expect(screen.getByText('My Playlist')).toBeInTheDocument()
      expect(screen.getByText('Another Playlist')).toBeInTheDocument()
    })
  })

  it('shows video count on playlist cards', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({
          playlists: [
            { id: 'PL1', title: 'My Playlist', video_count: 5, privacy_status: 'private', description: '', source: 'api', last_synced: '' },
          ],
        })
      ),
    )
    renderPlaylists()
    await waitFor(() => {
      expect(screen.getByText('5 videos')).toBeInTheDocument()
    })
  })

  it('shows privacy badge on playlist cards', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({
          playlists: [
            { id: 'PL1', title: 'My Playlist', video_count: 5, privacy_status: 'private', description: '', source: 'api', last_synced: '' },
          ],
        })
      ),
    )
    renderPlaylists()
    await waitFor(() => {
      expect(screen.getByText('private')).toBeInTheDocument()
    })
  })

  it('shows delete button on playlist cards', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({
          playlists: [
            { id: 'PL1', title: 'My Playlist', video_count: 5, privacy_status: 'private', description: '', source: 'api', last_synced: '' },
          ],
        })
      ),
    )
    renderPlaylists()
    await waitFor(() => {
      expect(screen.getByLabelText('Delete playlist')).toBeInTheDocument()
    })
  })

  it('opens create playlist dialog when button clicked', async () => {
    const user = userEvent.setup()
    renderPlaylists()
    await user.click(screen.getByText('Create Playlist'))
    await waitFor(() => {
      expect(screen.getByText('Create New Playlist')).toBeInTheDocument()
    })
  })

  it('opens confirm dialog when delete button clicked with playlist name and video count', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({
          playlists: [
            { id: 'PL1', title: 'My Playlist', video_count: 5, privacy_status: 'private', description: '', source: 'api', last_synced: '' },
          ],
        })
      ),
    )
    const user = userEvent.setup()
    renderPlaylists()
    await waitFor(() => {
      expect(screen.getByText('My Playlist')).toBeInTheDocument()
    })
    await user.click(screen.getByLabelText('Delete playlist'))
    await waitFor(() => {
      expect(screen.getByText(/Permanently delete "My Playlist" and its 5 videos/)).toBeInTheDocument()
    })
  })
})
