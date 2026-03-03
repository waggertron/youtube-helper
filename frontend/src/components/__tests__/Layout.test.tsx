import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import Layout from '../Layout'

function renderWithProviders(ui: React.ReactElement, route = '/') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[route]}>
          {ui}
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('Layout', () => {
  it('renders the sidebar with navigation items', () => {
    renderWithProviders(<Layout />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Playlists')).toBeInTheDocument()
    expect(screen.getByText('Watch Later')).toBeInTheDocument()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('Liked Videos')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the app title', () => {
    renderWithProviders(<Layout />)
    expect(screen.getByText('YouTube Helper')).toBeInTheDocument()
  })
})
