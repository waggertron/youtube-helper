import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../../test/render'
import QueuePanel from '../QueuePanel'
import type { QueueOp } from '../../api/client'

const mockOperations: QueueOp[] = [
  {
    id: 1,
    type: 'sync',
    status: 'active',
    progress: 50,
    message: 'Syncing...',
    error: '',
    params: '{}',
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:01Z',
    completed_at: null,
  },
  {
    id: 2,
    type: 'scrape',
    status: 'pending',
    progress: 0,
    message: '',
    error: '',
    params: '{}',
    created_at: '2026-01-01T00:00:02Z',
    started_at: null,
    completed_at: null,
  },
  {
    id: 3,
    type: 'export',
    status: 'failed',
    progress: 30,
    message: '',
    error: 'Network error',
    params: '{}',
    created_at: '2026-01-01T00:00:03Z',
    started_at: '2026-01-01T00:00:04Z',
    completed_at: '2026-01-01T00:00:05Z',
  },
  {
    id: 4,
    type: 'sync',
    status: 'completed',
    progress: 100,
    message: 'Done',
    error: '',
    params: '{}',
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:01Z',
    completed_at: '2026-01-01T00:00:10Z',
  },
]

const noop = () => {}

describe('QueuePanel', () => {
  it('shows active operation with progress', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    expect(screen.getByText('Syncing...')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('shows pending operations', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    expect(screen.getByText(/scrape/i)).toBeInTheDocument()
  })

  it('shows failed operations with error', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('has retry button for failed operations', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    // MUI Tooltip sets aria-label to the tooltip text on the child button
    expect(screen.getByRole('button', { name: /re-run this failed operation/i })).toBeInTheDocument()
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  it('has skip button for failed operations', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    expect(screen.getByRole('button', { name: /mark this operation as skipped/i })).toBeInTheDocument()
    expect(screen.getByText('Skip')).toBeInTheDocument()
  })

  it('has cancel button for pending operations', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    expect(screen.getByRole('button', { name: /remove this operation from the queue/i })).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('shows completed operations', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={true} onClose={noop} />,
    )
    // The completed operation's type should be visible
    const completedSection = screen.getByText(/completed/i)
    expect(completedSection).toBeInTheDocument()
  })

  it('does not render content when closed', () => {
    renderWithProviders(
      <QueuePanel operations={mockOperations} open={false} onClose={noop} />,
    )
    // When closed, the drawer content should not be visible
    expect(screen.queryByText('Syncing...')).not.toBeInTheDocument()
  })
})
