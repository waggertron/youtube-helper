import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import VideoTable from '../VideoTable'
import { renderWithProviders } from '../../test/render'

const videos = [
  { id: 'V1', title: 'Video One', channel_name: 'Ch A', channel_id: 'CA', duration: 600, watch_progress: 75, thumbnail_url: '', published_at: '', is_liked: 1 },
  { id: 'V2', title: 'Video Two', channel_name: 'Ch B', channel_id: 'CB', duration: 120, watch_progress: 0, thumbnail_url: 'https://example.com/thumb.jpg', published_at: '', is_liked: null },
]

describe('VideoTable', () => {
  describe('compact view (default)', () => {
    it('renders video titles as links to YouTube', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      const link = screen.getByRole('link', { name: /Video One/ })
      expect(link).toHaveAttribute('href', 'https://www.youtube.com/watch?v=V1')
      expect(link).toHaveAttribute('target', '_blank')
    })

    it('renders channel names', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.getByText('Ch A')).toBeInTheDocument()
      expect(screen.getByText('Ch B')).toBeInTheDocument()
    })

    it('renders formatted duration', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.getByText('10:00')).toBeInTheDocument()
      expect(screen.getByText('2:00')).toBeInTheDocument()
    })

    it('renders progress for videos with watch progress', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('renders row numbers', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.getByText('1')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('renders table headers', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.getByText('#')).toBeInTheDocument()
      expect(screen.getByText('Title')).toBeInTheDocument()
      expect(screen.getByText('Channel')).toBeInTheDocument()
      expect(screen.getByText('Duration')).toBeInTheDocument()
      expect(screen.getByText('Progress')).toBeInTheDocument()
      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('shows remove button when onRemove is provided', () => {
      const onRemove = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onRemove={onRemove} />)
      const removeButtons = screen.getAllByLabelText('Remove')
      expect(removeButtons).toHaveLength(2)
    })

    it('calls onRemove with video id when remove button is clicked', async () => {
      const user = userEvent.setup()
      const onRemove = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onRemove={onRemove} />)
      const removeButtons = screen.getAllByLabelText('Remove')
      await user.click(removeButtons[0])
      expect(onRemove).toHaveBeenCalledWith('V1')
    })

    it('shows like button when onLike is provided', () => {
      const onLike = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onLike={onLike} />)
      const likeButtons = screen.getAllByLabelText('Like')
      expect(likeButtons).toHaveLength(2)
    })

    it('calls onLike with video id when like button is clicked', async () => {
      const user = userEvent.setup()
      const onLike = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onLike={onLike} />)
      const likeButtons = screen.getAllByLabelText('Like')
      // V1 is liked (disabled), so click V2's like button
      await user.click(likeButtons[1])
      expect(onLike).toHaveBeenCalledWith('V2')
    })

    it('hides remove and like buttons when no callbacks provided', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.queryByLabelText('Remove')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Like')).not.toBeInTheDocument()
    })

    it('renders empty state when no videos', () => {
      renderWithProviders(<VideoTable videos={[]} />)
      expect(screen.getByText('#')).toBeInTheDocument()
    })
  })

  describe('download button', () => {
    it('always shows download buttons', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      const downloadButtons = screen.getAllByLabelText('Download')
      expect(downloadButtons).toHaveLength(2)
    })

    it('links to cobalt.tools with encoded youtube URL', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      const downloadButtons = screen.getAllByLabelText('Download')
      const expectedUrl = `https://www.cobalt.tools/?u=${encodeURIComponent('https://www.youtube.com/watch?v=V1')}`
      expect(downloadButtons[0].closest('a')).toHaveAttribute('href', expectedUrl)
    })
  })

  describe('play button', () => {
    it('shows play button when onPlay is provided', () => {
      const onPlay = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onPlay={onPlay} />)
      const playButtons = screen.getAllByLabelText('Play')
      expect(playButtons).toHaveLength(2)
    })

    it('does not show play button when onPlay is not provided', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      expect(screen.queryByLabelText('Play')).not.toBeInTheDocument()
    })

    it('calls onPlay with video id when play button is clicked', async () => {
      const user = userEvent.setup()
      const onPlay = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onPlay={onPlay} />)
      const playButtons = screen.getAllByLabelText('Play')
      await user.click(playButtons[0])
      expect(onPlay).toHaveBeenCalledWith('V1')
    })
  })

  describe('liked indicator', () => {
    it('shows liked indicator for liked videos', () => {
      renderWithProviders(<VideoTable videos={videos} />)
      // V1 has is_liked=1, should show a ThumbUp icon with "Liked" tooltip
      const likedIcons = screen.getAllByTestId('ThumbUpIcon')
      // At minimum there should be one for the liked indicator on V1
      expect(likedIcons.length).toBeGreaterThanOrEqual(1)
    })

    it('disables like button for already-liked videos', () => {
      const onLike = vi.fn()
      renderWithProviders(<VideoTable videos={videos} onLike={onLike} />)
      const likeButtons = screen.getAllByLabelText('Like')
      // V1 is liked, its like button should be disabled
      expect(likeButtons[0]).toBeDisabled()
      // V2 is not liked, its like button should be enabled
      expect(likeButtons[1]).not.toBeDisabled()
    })
  })

  describe('extraColumns render prop', () => {
    it('renders extra content for each video', () => {
      const extraColumns = (video: { id: string }) => <span data-testid={`extra-${video.id}`}>Extra {video.id}</span>
      renderWithProviders(<VideoTable videos={videos} extraColumns={extraColumns} />)
      expect(screen.getByTestId('extra-V1')).toBeInTheDocument()
      expect(screen.getByTestId('extra-V2')).toBeInTheDocument()
    })
  })

  describe('list view', () => {
    it('renders thumbnail column', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="list" />)
      expect(screen.getByText('Thumbnail')).toBeInTheDocument()
    })

    it('renders thumbnail images as links', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="list" />)
      const images = screen.getAllByRole('img')
      expect(images.length).toBeGreaterThanOrEqual(2)
    })

    it('uses fallback thumbnail when thumbnail_url is empty', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="list" />)
      const images = screen.getAllByRole('img')
      // V1 has empty thumbnail_url, should use ytimg fallback
      expect(images[0]).toHaveAttribute('src', 'https://i.ytimg.com/vi/V1/mqdefault.jpg')
      // V2 has a thumbnail_url set
      expect(images[1]).toHaveAttribute('src', 'https://example.com/thumb.jpg')
    })

    it('renders titles as YouTube links', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="list" />)
      const links = screen.getAllByRole('link', { name: /Video One/ })
      // Both thumbnail link and title link match; at least one should point to YouTube
      const titleLink = links.find(l => l.textContent === 'Video One')
      expect(titleLink).toHaveAttribute('href', 'https://www.youtube.com/watch?v=V1')
    })
  })

  describe('grid view', () => {
    it('renders card-based layout', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="grid" />)
      // Grid view uses Typography for titles, check they render
      expect(screen.getByText('Video One')).toBeInTheDocument()
      expect(screen.getByText('Video Two')).toBeInTheDocument()
    })

    it('renders thumbnails in grid cards', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="grid" />)
      const images = screen.getAllByRole('img')
      expect(images.length).toBeGreaterThanOrEqual(2)
    })

    it('renders duration as chip', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="grid" />)
      expect(screen.getByText('10:00')).toBeInTheDocument()
      expect(screen.getByText('2:00')).toBeInTheDocument()
    })

    it('renders watch progress as chip when > 0', () => {
      renderWithProviders(<VideoTable videos={videos} viewMode="grid" />)
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('renders action buttons in grid cards', () => {
      const onRemove = vi.fn()
      renderWithProviders(<VideoTable videos={videos} viewMode="grid" onRemove={onRemove} />)
      const removeButtons = screen.getAllByLabelText('Remove')
      expect(removeButtons).toHaveLength(2)
    })
  })
})
