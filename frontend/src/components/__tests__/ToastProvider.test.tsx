import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import theme from '../../theme'
import { ToastProvider, useToast } from '../ToastProvider'

function TestComponent() {
  const toast = useToast()
  return (
    <div>
      <button onClick={() => toast.success('It worked!')}>Show Success</button>
      <button onClick={() => toast.error('Something failed')}>Show Error</button>
      <button onClick={() => toast.info('FYI')}>Show Info</button>
    </div>
  )
}

function renderWithToast(ui: React.ReactElement) {
  return render(
    <ThemeProvider theme={theme}>
      <ToastProvider>{ui}</ToastProvider>
    </ThemeProvider>,
  )
}

describe('ToastProvider', () => {
  it('provides toast context', () => {
    renderWithToast(<TestComponent />)
    expect(screen.getByText('Show Success')).toBeInTheDocument()
  })

  it('shows a success toast when success is called', async () => {
    const user = userEvent.setup()
    renderWithToast(<TestComponent />)
    await user.click(screen.getByText('Show Success'))
    expect(screen.getByText('It worked!')).toBeInTheDocument()
  })

  it('shows an error toast when error is called', async () => {
    const user = userEvent.setup()
    renderWithToast(<TestComponent />)
    await user.click(screen.getByText('Show Error'))
    expect(screen.getByText('Something failed')).toBeInTheDocument()
  })

  it('shows an info toast when info is called', async () => {
    const user = userEvent.setup()
    renderWithToast(<TestComponent />)
    await user.click(screen.getByText('Show Info'))
    expect(screen.getByText('FYI')).toBeInTheDocument()
  })
})
