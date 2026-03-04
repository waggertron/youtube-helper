import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import VideoFilters from '../VideoFilters'
import { renderWithProviders } from '../../test/render'

const videos = [
  { id: 'V1', title: 'Alpha Video', channel_name: 'Zebra Channel', channel_id: 'C1', duration: 300, watch_progress: 50, thumbnail_url: '', published_at: '', is_liked: 1 },
  { id: 'V2', title: 'Beta Video', channel_name: 'Apple Channel', channel_id: 'C2', duration: 120, watch_progress: 0, thumbnail_url: '', published_at: '', is_liked: null },
  { id: 'V3', title: 'Gamma Video', channel_name: 'Mango Channel', channel_id: 'C3', duration: 600, watch_progress: 75, thumbnail_url: '', published_at: '', is_liked: 1 },
]

describe('VideoFilters', () => {
  it('renders filter controls', () => {
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div>{filtered.length} videos</div>}
      </VideoFilters>
    )
    expect(screen.getByPlaceholderText('Filter by title or channel...')).toBeInTheDocument()
  })

  it('renders all videos initially', () => {
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div data-testid="count">{filtered.length} videos</div>}
      </VideoFilters>
    )
    expect(screen.getByTestId('count')).toHaveTextContent('3 videos')
  })

  it('filters videos by search text matching title', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div data-testid="count">{filtered.length} videos</div>}
      </VideoFilters>
    )
    await user.type(screen.getByPlaceholderText('Filter by title or channel...'), 'Alpha')
    expect(screen.getByTestId('count')).toHaveTextContent('1 videos')
  })

  it('filters videos by search text matching channel name', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div data-testid="count">{filtered.length} videos</div>}
      </VideoFilters>
    )
    await user.type(screen.getByPlaceholderText('Filter by title or channel...'), 'Mango')
    expect(screen.getByTestId('count')).toHaveTextContent('1 videos')
  })

  it('search is case-insensitive', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div data-testid="count">{filtered.length} videos</div>}
      </VideoFilters>
    )
    await user.type(screen.getByPlaceholderText('Filter by title or channel...'), 'alpha')
    expect(screen.getByTestId('count')).toHaveTextContent('1 videos')
  })

  it('shows liked filter when showLikedFilter is true', () => {
    renderWithProviders(
      <VideoFilters videos={videos} showLikedFilter>
        {(filtered) => <div>{filtered.length}</div>}
      </VideoFilters>
    )
    // MUI renders labels that can be found by their combobox role
    const comboboxes = screen.getAllByRole('combobox')
    // With showLikedFilter, there should be 3 comboboxes: Sort by, Order, Liked
    expect(comboboxes).toHaveLength(3)
  })

  it('hides liked filter by default', () => {
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div>{filtered.length}</div>}
      </VideoFilters>
    )
    // Without showLikedFilter, there should be 2 comboboxes: Sort by, Order
    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes).toHaveLength(2)
  })

  it('renders sort by and order dropdowns', () => {
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => <div>{filtered.length}</div>}
      </VideoFilters>
    )
    const comboboxes = screen.getAllByRole('combobox')
    expect(comboboxes).toHaveLength(2)
    // Verify default values are shown
    expect(comboboxes[0]).toHaveTextContent('Title')
    expect(comboboxes[1]).toHaveTextContent('Asc')
  })

  it('sorts videos by title ascending by default', () => {
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => (
          <div data-testid="titles">{filtered.map(v => v.title).join(',')}</div>
        )}
      </VideoFilters>
    )
    expect(screen.getByTestId('titles')).toHaveTextContent('Alpha Video,Beta Video,Gamma Video')
  })

  it('passes filtered results to children render prop', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <VideoFilters videos={videos}>
        {(filtered) => (
          <ul>
            {filtered.map(v => <li key={v.id}>{v.title}</li>)}
          </ul>
        )}
      </VideoFilters>
    )
    await user.type(screen.getByPlaceholderText('Filter by title or channel...'), 'Beta')
    expect(screen.getByText('Beta Video')).toBeInTheDocument()
    expect(screen.queryByText('Alpha Video')).not.toBeInTheDocument()
    expect(screen.queryByText('Gamma Video')).not.toBeInTheDocument()
  })
})
