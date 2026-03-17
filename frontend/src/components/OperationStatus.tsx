import { useEffect, useState } from 'react'
import { Alert, Box, LinearProgress, Typography } from '@mui/material'
import type { TaskStatus } from '../api/client'

interface Props {
  status: TaskStatus | null | undefined
  label: string
}

export default function OperationStatus({ status, label }: Props) {
  const [dismissed, setDismissed] = useState(false)

  useEffect(() => {
    if (status?.status === 'completed' || status?.status === 'failed') {
      const timer = setTimeout(() => setDismissed(true), 8000)
      return () => clearTimeout(timer)
    }
    setDismissed(false)
  }, [status?.status])

  if (!status || status.status === 'idle' || dismissed) return null

  if (status.status === 'running') {
    return (
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2" color="text.secondary">
            {status.message || `${label} in progress...`}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {status.progress}%
          </Typography>
        </Box>
        <LinearProgress variant="determinate" value={status.progress} />
      </Box>
    )
  }

  if (status.status === 'completed') {
    return (
      <Alert severity="success" sx={{ mb: 2 }}>
        <strong>{label} complete.</strong> {status.message}
      </Alert>
    )
  }

  if (status.status === 'failed') {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        <strong>{label} failed.</strong> {status.error}
      </Alert>
    )
  }

  return null
}
