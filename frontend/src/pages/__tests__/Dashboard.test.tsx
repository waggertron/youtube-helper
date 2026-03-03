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
    expect(screen.getByText('Scrape Watch Later')).toBeInTheDocument()
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
        return HttpResponse.json({ operation_id: 1, message: 'Sync queued' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(<Dashboard />)
    await user.click(screen.getByText('Sync Playlists'))
    await waitFor(() => expect(syncCalled).toBe(true))
  })

  it('scrape button triggers mutation', async () => {
    let scrapeCalled = false
    server.use(
      http.post('/api/watch-later/scrape', () => {
        scrapeCalled = true
        return HttpResponse.json({ operation_id: 2, message: 'Scrape queued' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(<Dashboard />)
    await user.click(screen.getByText('Scrape Watch Later'))
    await waitFor(() => expect(scrapeCalled).toBe(true))
  })

  it('shows queue status when operations are active', async () => {
    server.use(
      http.get('/api/queue', () =>
        HttpResponse.json({ operations: [
          { id: 1, type: 'sync', status: 'active', progress: 50, message: 'Syncing...', error: '', params: '{}', created_at: '', started_at: '', completed_at: null },
          { id: 2, type: 'scrape', status: 'pending', progress: 0, message: '', error: '', params: '{}', created_at: '', started_at: null, completed_at: null },
        ] })
      ),
    )
    renderWithProviders(<Dashboard />)
    await waitFor(() => {
      expect(screen.getByText('Queue Status')).toBeInTheDocument()
      expect(screen.getByText(/sync: Syncing\.\.\. \(50%\)/)).toBeInTheDocument()
      expect(screen.getByText('1 pending')).toBeInTheDocument()
    })
  })

  it('hides queue status when no active or pending operations', async () => {
    server.use(
      http.get('/api/queue', () =>
        HttpResponse.json({ operations: [] })
      ),
    )
    renderWithProviders(<Dashboard />)
    // Give time for query to resolve
    await waitFor(() => {
      expect(screen.queryByText('Queue Status')).not.toBeInTheDocument()
    })
  })
})
