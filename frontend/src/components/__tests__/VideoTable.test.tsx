import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import VideoTable from '../VideoTable'
import { renderWithProviders } from '../../test/render'

const videos = [
  { id: 'V1', title: 'Video One', channel_name: 'Ch A', channel_id: 'CA', duration: 600, watch_progress: 75, thumbnail_url: '', published_at: '' },
  { id: 'V2', title: 'Video Two', channel_name: 'Ch B', channel_id: 'CB', duration: 120, watch_progress: 0, thumbnail_url: '', published_at: '' },
]

describe('VideoTable', () => {
  it('renders video titles', () => {
    renderWithProviders(<VideoTable videos={videos} />)
    expect(screen.getByText('Video One')).toBeInTheDocument()
    expect(screen.getByText('Video Two')).toBeInTheDocument()
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
    await user.click(likeButtons[0])
    expect(onLike).toHaveBeenCalledWith('V1')
  })

  it('hides action buttons when no callbacks provided', () => {
    renderWithProviders(<VideoTable videos={videos} />)
    expect(screen.queryByLabelText('Remove')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Like')).not.toBeInTheDocument()
  })

  it('renders empty state when no videos', () => {
    renderWithProviders(<VideoTable videos={[]} />)
    expect(screen.getByText('#')).toBeInTheDocument()
  })
})
