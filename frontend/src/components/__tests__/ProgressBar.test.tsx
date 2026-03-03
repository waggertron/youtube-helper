import { screen } from '@testing-library/react'
import ProgressBar from '../ProgressBar'
import { renderWithProviders } from '../../test/render'

describe('ProgressBar', () => {
  it('renders with percentage text', () => {
    renderWithProviders(<ProgressBar value={75} />)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('renders 0% progress', () => {
    renderWithProviders(<ProgressBar value={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders the MUI LinearProgress bar', () => {
    renderWithProviders(<ProgressBar value={50} />)
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('passes the correct value to the progress bar', () => {
    renderWithProviders(<ProgressBar value={42} />)
    const progressbar = screen.getByRole('progressbar')
    expect(progressbar).toHaveAttribute('aria-valuenow', '42')
  })
})
