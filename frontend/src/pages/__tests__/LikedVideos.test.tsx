import { screen, waitFor } from '@testing-library/react'
import LikedVideos from '../LikedVideos'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'

describe('LikedVideos', () => {
  it('renders the page heading', () => {
    renderWithProviders(<LikedVideos />)
    expect(screen.getByText('Liked Videos')).toBeInTheDocument()
  })

  it('displays liked videos from API', async () => {
    server.use(
      http.get('/api/videos/liked', () =>
        HttpResponse.json({
          videos: [
            {
              id: 'V1',
              title: 'My Liked Video',
              channel_name: 'Favorite Channel',
              channel_id: 'C1',
              duration: 300,
              watch_progress: 0,
              thumbnail_url: '',
              published_at: '2024-06-15',
            },
          ],
        }),
      ),
    )
    renderWithProviders(<LikedVideos />)
    await waitFor(() =>
      expect(screen.getByText('My Liked Video')).toBeInTheDocument(),
    )
  })
})
