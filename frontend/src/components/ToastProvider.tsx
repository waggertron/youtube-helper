import { createContext, useContext, useState, useCallback } from 'react'
import { Snackbar, Alert, type AlertColor } from '@mui/material'

interface ToastContextValue {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}

interface ToastState {
  open: boolean
  message: string
  severity: AlertColor
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toast, setToast] = useState<ToastState>({
    open: false,
    message: '',
    severity: 'info',
  })

  const show = useCallback((message: string, severity: AlertColor) => {
    setToast({ open: true, message, severity })
  }, [])

  const handleClose = useCallback(
    (_event?: React.SyntheticEvent | Event, reason?: string) => {
      if (reason === 'clickaway') return
      setToast((prev) => ({ ...prev, open: false }))
    },
    [],
  )

  const value: ToastContextValue = {
    success: useCallback((msg: string) => show(msg, 'success'), [show]),
    error: useCallback((msg: string) => show(msg, 'error'), [show]),
    info: useCallback((msg: string) => show(msg, 'info'), [show]),
  }

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleClose}
          severity={toast.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </ToastContext.Provider>
  )
}
