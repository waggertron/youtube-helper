import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Search from '../Search'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'

describe('Search', () => {
  it('renders search input', () => {
    renderWithProviders(<Search />)
    expect(screen.getByPlaceholderText(/search videos/i)).toBeInTheDocument()
  })

  it('shows description text about fuzzy matching', () => {
    renderWithProviders(<Search />)
    expect(screen.getByText(/fuzzy matching/i)).toBeInTheDocument()
  })

  it('displays results when search returns data', async () => {
    server.use(
      http.get('/api/search', () =>
        HttpResponse.json({
          query: 'python',
          results: [
            { type: 'video', id: 'V1', title: 'Python Tutorial', channel_name: 'Ch', score: 90 },
            { type: 'playlist', id: 'PL1', title: 'Python Playlist', score: 85 },
          ],
        }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(<Search />)
    const input = screen.getByPlaceholderText(/search videos/i)
    await user.type(input, 'python')
    await waitFor(() =>
      expect(screen.getByText('Python Tutorial')).toBeInTheDocument(),
    )
    expect(screen.getByText('Python Playlist')).toBeInTheDocument()
  })

  it('groups results into Videos and Playlists sections', async () => {
    server.use(
      http.get('/api/search', () =>
        HttpResponse.json({
          query: 'python',
          results: [
            { type: 'video', id: 'V1', title: 'Python Tutorial', channel_name: 'Ch', score: 90 },
            { type: 'playlist', id: 'PL1', title: 'Python Playlist', score: 85 },
          ],
        }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(<Search />)
    const input = screen.getByPlaceholderText(/search videos/i)
    await user.type(input, 'python')
    await waitFor(() =>
      expect(screen.getByText('Videos')).toBeInTheDocument(),
    )
    expect(screen.getByText('Playlists')).toBeInTheDocument()
  })

  it('shows match score for results', async () => {
    server.use(
      http.get('/api/search', () =>
        HttpResponse.json({
          query: 'python',
          results: [
            { type: 'video', id: 'V1', title: 'Python Tutorial', channel_name: 'Ch', score: 90 },
          ],
        }),
      ),
    )
    const user = userEvent.setup()
    renderWithProviders(<Search />)
    const input = screen.getByPlaceholderText(/search videos/i)
    await user.type(input, 'python')
    await waitFor(() =>
      expect(screen.getByText('90')).toBeInTheDocument(),
    )
  })

  it('shows no results when search returns empty', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Search />)
    const input = screen.getByPlaceholderText(/search videos/i)
    await user.type(input, 'xyznotfound')
    await waitFor(() =>
      expect(screen.getByText(/no results/i)).toBeInTheDocument(),
    )
  })
})
