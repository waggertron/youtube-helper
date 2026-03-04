import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LikedVideos from '../LikedVideos'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'

const likedVideosData = {
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
    {
      id: 'V2',
      title: 'Another Liked Video',
      channel_name: 'Other Channel',
      channel_id: 'C2',
      duration: 180,
      watch_progress: 50,
      thumbnail_url: '',
      published_at: '2024-07-01',
    },
  ],
}

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

  it('shows confirm dialog with video title when unlike is clicked', async () => {
    server.use(
      http.get('/api/videos/liked', () => HttpResponse.json(likedVideosData)),
    )
    const user = userEvent.setup()
    renderWithProviders(<LikedVideos />)
    await waitFor(() => {
      expect(screen.getByText('My Liked Video')).toBeInTheDocument()
    })
    // Videos are sorted alphabetically by title, so "Another Liked Video" is first
    const removeButtons = screen.getAllByLabelText('Remove')
    await user.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByText('Unlike Video')).toBeInTheDocument()
      expect(screen.getByText(/Unlike "Another Liked Video"/)).toBeInTheDocument()
    })
  })

  it('does not call unlike mutation until confirm is clicked', async () => {
    let unlikeCalled = false
    server.use(
      http.get('/api/videos/liked', () => HttpResponse.json(likedVideosData)),
      http.delete('/api/videos/:videoId/like', () => {
        unlikeCalled = true
        return HttpResponse.json({ operation_id: 1, message: 'Unlike queued' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(<LikedVideos />)
    await waitFor(() => {
      expect(screen.getByText('My Liked Video')).toBeInTheDocument()
    })
    const removeButtons = screen.getAllByLabelText('Remove')
    await user.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByText('Unlike Video')).toBeInTheDocument()
    })
    expect(unlikeCalled).toBe(false)
    await user.click(screen.getByText('Confirm'))
    await waitFor(() => expect(unlikeCalled).toBe(true))
  })

  it('cancels unlike when cancel is clicked in confirm dialog', async () => {
    server.use(
      http.get('/api/videos/liked', () => HttpResponse.json(likedVideosData)),
    )
    const user = userEvent.setup()
    renderWithProviders(<LikedVideos />)
    await waitFor(() => {
      expect(screen.getByText('My Liked Video')).toBeInTheDocument()
    })
    const removeButtons = screen.getAllByLabelText('Remove')
    await user.click(removeButtons[0])
    await waitFor(() => {
      expect(screen.getByText('Unlike Video')).toBeInTheDocument()
    })
    await user.click(screen.getByText('Cancel'))
    await waitFor(() => {
      expect(screen.queryByText('Unlike Video')).not.toBeInTheDocument()
    })
  })
})
