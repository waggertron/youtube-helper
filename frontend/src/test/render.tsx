import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import theme from '../theme'

export function renderWithProviders(ui: React.ReactElement, route = '/') {
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
