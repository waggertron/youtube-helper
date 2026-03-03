import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ConfirmDialog from '../ConfirmDialog'
import { renderWithProviders } from '../../test/render'

describe('ConfirmDialog', () => {
  it('renders title and description when open', () => {
    renderWithProviders(
      <ConfirmDialog
        open={true}
        title="Delete Playlist"
        description="Are you sure you want to delete this playlist?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByText('Delete Playlist')).toBeInTheDocument()
    expect(screen.getByText('Are you sure you want to delete this playlist?')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    renderWithProviders(
      <ConfirmDialog
        open={false}
        title="Delete Playlist"
        description="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.queryByText('Delete Playlist')).not.toBeInTheDocument()
  })

  it('calls onConfirm when confirm clicked', async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    renderWithProviders(
      <ConfirmDialog
        open={true}
        title="Delete Playlist"
        description="Are you sure?"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    )
    await user.click(screen.getByText('Confirm'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when cancel clicked', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()
    renderWithProviders(
      <ConfirmDialog
        open={true}
        title="Delete Playlist"
        description="Are you sure?"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    )
    await user.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('renders Confirm and Cancel buttons', () => {
    renderWithProviders(
      <ConfirmDialog
        open={true}
        title="Confirm Action"
        description="This action cannot be undone."
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })
})
