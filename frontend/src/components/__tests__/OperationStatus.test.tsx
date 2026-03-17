import { screen, act, render } from '@testing-library/react'
import { vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material'
import { MemoryRouter } from 'react-router-dom'
import theme from '../../theme'
import { ToastProvider } from '../ToastProvider'
import { renderWithProviders } from '../../test/render'
import OperationStatus from '../OperationStatus'

function wrapProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/']}>
            {ui}
          </MemoryRouter>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

describe('OperationStatus', () => {
  it('renders nothing when status is idle', () => {
    const { container } = renderWithProviders(
      <OperationStatus status={{ status: 'idle', progress: 0, message: '', error: null }} label="Sync" />
    )
    expect(container.querySelector('.MuiAlert-root, .MuiLinearProgress-root')).toBeNull()
  })

  it('renders nothing when status is null', () => {
    const { container } = renderWithProviders(
      <OperationStatus status={null} label="Sync" />
    )
    expect(container.querySelector('.MuiAlert-root, .MuiLinearProgress-root')).toBeNull()
  })

  it('shows progress bar and message when running', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'running', progress: 50, message: 'Syncing playlists...', error: null }}
        label="Sync"
      />
    )
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.getByText('Syncing playlists...')).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('shows default message when running with no message', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'running', progress: 10, message: '', error: null }}
        label="Sync"
      />
    )
    expect(screen.getByText('Sync in progress...')).toBeInTheDocument()
  })

  it('shows success alert when completed', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'completed', progress: 100, message: 'Synced 12 playlists', error: null }}
        label="Sync"
      />
    )
    expect(screen.getByText(/Sync complete/)).toBeInTheDocument()
    expect(screen.getByText('Synced 12 playlists')).toBeInTheDocument()
  })

  it('shows error alert when failed', () => {
    renderWithProviders(
      <OperationStatus
        status={{ status: 'failed', progress: 30, message: '', error: 'Network error' }}
        label="Sync"
      />
    )
    expect(screen.getByText(/Sync failed/)).toBeInTheDocument()
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('auto-dismisses completed status after 8 seconds', () => {
    vi.useFakeTimers()
    const { container } = renderWithProviders(
      <OperationStatus
        status={{ status: 'completed', progress: 100, message: 'Done', error: null }}
        label="Sync"
      />
    )
    expect(screen.getByText(/Sync complete/)).toBeInTheDocument()

    act(() => { vi.advanceTimersByTime(8000) })

    expect(container.querySelector('.MuiAlert-root')).toBeNull()
    vi.useRealTimers()
  })

  it('auto-dismisses failed status after 8 seconds', () => {
    vi.useFakeTimers()
    const { container } = renderWithProviders(
      <OperationStatus
        status={{ status: 'failed', progress: 0, message: '', error: 'Oops' }}
        label="Sync"
      />
    )
    expect(screen.getByText(/Sync failed/)).toBeInTheDocument()

    act(() => { vi.advanceTimersByTime(8000) })

    expect(container.querySelector('.MuiAlert-root')).toBeNull()
    vi.useRealTimers()
  })

  it('resets dismissed state when status goes back to running', () => {
    vi.useFakeTimers()
    const { rerender } = render(
      wrapProviders(
        <OperationStatus
          status={{ status: 'completed', progress: 100, message: 'Done', error: null }}
          label="Sync"
        />
      )
    )
    act(() => { vi.advanceTimersByTime(8000) })

    // Now simulate a new run
    rerender(
      wrapProviders(
        <OperationStatus
          status={{ status: 'running', progress: 10, message: 'Starting...', error: null }}
          label="Sync"
        />
      )
    )
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    vi.useRealTimers()
  })
})
