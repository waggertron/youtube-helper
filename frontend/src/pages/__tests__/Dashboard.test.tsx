import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Dashboard from '../Dashboard'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'

describe('Dashboard', () => {
  it('renders the dashboard heading', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('shows stat cards', async () => {
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Playlists')).toBeInTheDocument()
      expect(screen.getByText('Total Videos')).toBeInTheDocument()
      expect(screen.getByText('Watch Later')).toBeInTheDocument()
    })
  })

  it('shows quick action buttons', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Sync Playlists')).toBeInTheDocument()
  })

  it('displays playlist count from API', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({ playlists: [
          { id: 'PL1', title: 'Test', video_count: 5 },
          { id: 'PL2', title: 'Test2', video_count: 10 },
        ] })
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('2')).toBeInTheDocument())
  })

  it('displays total video count from API', async () => {
    server.use(
      http.get('/api/playlists', () =>
        HttpResponse.json({ playlists: [
          { id: 'PL1', title: 'Test', video_count: 5 },
          { id: 'PL2', title: 'Test2', video_count: 10 },
        ] })
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('15')).toBeInTheDocument())
  })

  it('displays watch later count from API', async () => {
    server.use(
      http.get('/api/watch-later', () =>
        HttpResponse.json({ videos: [
          { id: 'V1', title: 'Video 1' },
          { id: 'V2', title: 'Video 2' },
          { id: 'V3', title: 'Video 3' },
        ] })
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument())
  })

  it('sync button triggers mutation', async () => {
    let syncCalled = false
    server.use(
      http.post('/api/sync', () => {
        syncCalled = true
        return HttpResponse.json({ status: 'running', message: 'Sync started' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(<Dashboard />)
    await user.click(screen.getByText('Sync Playlists'))
    await waitFor(() => expect(syncCalled).toBe(true))
  })
})
