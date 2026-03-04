import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../Settings'
import { http, HttpResponse } from 'msw'
import { server } from '../../test/server'
import { renderWithProviders } from '../../test/render'

describe('Settings', () => {
  it('renders the page heading', () => {
    renderWithProviders(<Settings />)
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('shows auth status section', async () => {
    renderWithProviders(<Settings />)
    await waitFor(() =>
      expect(screen.getByText('Authentication')).toBeInTheDocument(),
    )
  })

  it('shows stepper at step 1 when not authenticated and no client secret', async () => {
    server.use(
      http.get('/api/auth/status', () =>
        HttpResponse.json({
          authenticated: false,
          has_client_secret: false,
          has_token: false,
        }),
      ),
    )
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByText('Upload Client Secret')).toBeInTheDocument()
      expect(screen.getByText('Authorize')).toBeInTheDocument()
    })
    // Upload step should be active (step 1) — the Choose File button is visible
    expect(screen.getByRole('button', { name: 'Choose File' })).toBeInTheDocument()
  })

  it('shows stepper at step 2 when has client secret but not authenticated', async () => {
    server.use(
      http.get('/api/auth/status', () =>
        HttpResponse.json({
          authenticated: false,
          has_client_secret: true,
          has_token: false,
        }),
      ),
    )
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByText('Authorize with Google')).toBeInTheDocument()
    })
  })

  it('shows "Authenticated" chip when authenticated', async () => {
    server.use(
      http.get('/api/auth/status', () =>
        HttpResponse.json({
          authenticated: true,
          has_client_secret: true,
          has_token: true,
        }),
      ),
    )
    renderWithProviders(<Settings />)
    await waitFor(() => {
      expect(screen.getByText('Authenticated')).toBeInTheDocument()
    })
    // Should not show stepper
    expect(screen.queryByText('Upload Client Secret')).not.toBeInTheDocument()
  })

  it('upload button calls uploadSecret API', async () => {
    let uploadCalled = false
    server.use(
      http.get('/api/auth/status', () =>
        HttpResponse.json({
          authenticated: false,
          has_client_secret: false,
          has_token: false,
        }),
      ),
      http.post('/api/auth/upload-secret', () => {
        uploadCalled = true
        return HttpResponse.json({ message: 'Client secret saved' })
      }),
    )
    const user = userEvent.setup()
    renderWithProviders(<Settings />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Choose File' })).toBeInTheDocument()
    })

    // Create a fake file and upload it
    const file = new File(['{"installed":{}}'], 'client_secret.json', {
      type: 'application/json',
    })
    const input = screen.getByTestId('secret-file-input') as HTMLInputElement
    await user.upload(input, file)

    await waitFor(() => expect(uploadCalled).toBe(true))
  })

  it('authorize button calls startAuth API', async () => {
    let startAuthCalled = false
    server.use(
      http.get('/api/auth/status', () =>
        HttpResponse.json({
          authenticated: false,
          has_client_secret: true,
          has_token: false,
        }),
      ),
      http.get('/api/auth/start', () => {
        startAuthCalled = true
        return HttpResponse.json({
          auth_url: 'https://accounts.google.com/o/oauth2/auth?fake=1',
        })
      }),
    )

    // Mock window.open to prevent actual navigation
    const mockOpen = vi.fn()
    vi.stubGlobal('open', mockOpen)

    const user = userEvent.setup()
    renderWithProviders(<Settings />)

    await waitFor(() => {
      expect(screen.getByText('Authorize with Google')).toBeInTheDocument()
    })

    await user.click(screen.getByText('Authorize with Google'))
    await waitFor(() => expect(startAuthCalled).toBe(true))

    vi.unstubAllGlobals()
  })

  it('shows success message when auth=success query param is present', async () => {
    server.use(
      http.get('/api/auth/status', () =>
        HttpResponse.json({
          authenticated: true,
          has_client_secret: true,
          has_token: true,
        }),
      ),
    )
    renderWithProviders(<Settings />, '/settings?auth=success')
    await waitFor(() => {
      expect(screen.getByText(/successfully authenticated/i)).toBeInTheDocument()
    })
  })
})
