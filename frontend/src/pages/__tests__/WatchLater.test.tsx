import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import WatchLater from '../WatchLater'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'

function getButtonByText(text: RegExp) {
  const buttons = screen.getAllByRole('button')
  const match = buttons.find((btn) => text.test(btn.textContent ?? ''))
  if (!match) throw new Error(`No button with text matching ${text}`)
  return match
}

const watchLaterVideos = [
  {
    id: 'V1',
    title: 'Test Video Title',
    channel_name: 'Test Channel',
    channel_id: 'C1',
    duration: 600,
    watch_progress: 50,
    thumbnail_url: '',
    published_at: '2024-01-01',
  },
  {
    id: 'V2',
    title: 'Watched Video',
    channel_name: 'Test Channel',
    channel_id: 'C1',
    duration: 300,
    watch_progress: 90,
    thumbnail_url: '',
    published_at: '2024-01-02',
  },
  {
    id: 'V3',
    title: 'Fully Watched',
    channel_name: 'Test Channel',
    channel_id: 'C1',
    duration: 120,
    watch_progress: 100,
    thumbnail_url: '',
    published_at: '2024-01-03',
  },
]

describe('WatchLater', () => {
  it('renders the page heading', () => {
    renderWithProviders(<WatchLater />)
    expect(screen.getByText('Watch Later')).toBeInTheDocument()
  })

  it('shows action buttons', () => {
    renderWithProviders(<WatchLater />)
    expect(getButtonByText(/^Import$/)).toBeInTheDocument()
    expect(getButtonByText(/^Export$/)).toBeInTheDocument()
    expect(getButtonByText(/^Purge$/)).toBeInTheDocument()
  })

  it('displays videos from API', async () => {
    server.use(
      http.get('/api/watch-later', () =>
        HttpResponse.json({
          videos: [
            {
              id: 'V1',
              title: 'Test Video Title',
              channel_name: 'Test Channel',
              channel_id: 'C1',
              duration: 600,
              watch_progress: 50,
              thumbnail_url: '',
              published_at: '2024-01-01',
            },
          ],
        }),
      ),
    )
    renderWithProviders(<WatchLater />)
    await waitFor(() =>
      expect(screen.getByText('Test Video Title')).toBeInTheDocument(),
    )
  })

  it('has a threshold slider', () => {
    renderWithProviders(<WatchLater />)
    expect(screen.getByText(/threshold/i)).toBeInTheDocument()
    expect(screen.getByRole('slider')).toBeInTheDocument()
  })

  it('import button has file input', () => {
    renderWithProviders(<WatchLater />)
    const importButton = getButtonByText(/^Import$/)
    const fileInput = importButton.querySelector('input[type="file"]')
    expect(fileInput).toBeInTheDocument()
    expect(fileInput).toHaveAttribute('accept', '.json,.csv')
  })

  it('export button shows confirmation dialog with video count', async () => {
    server.use(
      http.get('/api/watch-later', () =>
        HttpResponse.json({ videos: watchLaterVideos }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(<WatchLater />)
    await waitFor(() => {
      expect(screen.getByText('Test Video Title')).toBeInTheDocument()
    })
    await user.click(getButtonByText(/^Export$/))
    await waitFor(() => {
      expect(screen.getByText(/Confirm Export/i)).toBeInTheDocument()
      expect(screen.getByText(/Export 3 Watch Later videos/)).toBeInTheDocument()
    })
  })

  it('purge button shows confirmation dialog with watched video count', async () => {
    server.use(
      http.get('/api/watch-later', () =>
        HttpResponse.json({ videos: watchLaterVideos }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(<WatchLater />)
    await waitFor(() => {
      expect(screen.getByText('Test Video Title')).toBeInTheDocument()
    })
    await user.click(getButtonByText(/^Purge$/))
    await waitFor(() => {
      expect(screen.getByText(/Confirm Purge/i)).toBeInTheDocument()
      // Default threshold is 80%, so V2 (90%) and V3 (100%) are above threshold = 2 videos
      expect(screen.getByText(/Purge 2 videos watched above 80%/)).toBeInTheDocument()
    })
  })
})
