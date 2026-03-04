import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'
import AllVideos from '../AllVideos'

describe('AllVideos', () => {
  it('renders page heading', () => {
    renderWithProviders(<AllVideos />)
    expect(screen.getByText('All Videos')).toBeInTheDocument()
  })

  it('renders videos with playlist chips', async () => {
    server.use(
      http.get('/api/videos', () =>
        HttpResponse.json({
          videos: [
            {
              id: 'V1',
              title: 'Test Video',
              channel_name: 'Test Channel',
              channel_id: 'C1',
              duration: 300,
              watch_progress: 0,
              thumbnail_url: '',
              published_at: '',
              playlist_names: 'Playlist A,Playlist B',
              playlist_ids: 'PL1,PL2',
              is_liked: 1,
            },
          ],
        }),
      ),
    )
    renderWithProviders(<AllVideos />)
    await waitFor(() => {
      expect(screen.getByText('Test Video')).toBeInTheDocument()
      expect(screen.getByText('Playlist A')).toBeInTheDocument()
      expect(screen.getByText('Playlist B')).toBeInTheDocument()
    })
  })

  it('renders view mode toggle', () => {
    renderWithProviders(<AllVideos />)
    expect(screen.getByLabelText('Grid view')).toBeInTheDocument()
    expect(screen.getByLabelText('List view')).toBeInTheDocument()
    expect(screen.getByLabelText('Compact view')).toBeInTheDocument()
  })
})
