import { screen, waitFor } from '@testing-library/react'
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

  it('shows setup instructions when not authenticated', async () => {
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
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(/yt auth setup/),
    )
  })
})
