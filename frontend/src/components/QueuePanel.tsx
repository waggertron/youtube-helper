import {
  Box,
  Drawer,
  Typography,
  List,
  ListItem,
  LinearProgress,
  Button,
  Tooltip,
  IconButton,
  Chip,
} from '@mui/material'
import {
  CheckCircle as CheckIcon,
  Close as CloseIcon,
} from '@mui/icons-material'
import type { QueueOp } from '../api/client'
import { api } from '../api/client'
import { useQueryClient } from '@tanstack/react-query'

interface QueuePanelProps {
  operations: QueueOp[]
  open: boolean
  onClose: () => void
}

export default function QueuePanel({ operations, open, onClose }: QueuePanelProps) {
  const queryClient = useQueryClient()

  const active = operations.filter((op) => op.status === 'active')
  const pending = operations.filter((op) => op.status === 'pending')
  const failed = operations.filter((op) => op.status === 'failed')
  const completed = operations.filter((op) => op.status === 'completed')

  const invalidateQueue = () => {
    queryClient.invalidateQueries({ queryKey: ['queue'] })
  }

  const handleRetry = async (id: number) => {
    await api.retryOp(id)
    invalidateQueue()
  }

  const handleSkip = async (id: number) => {
    await api.skipOp(id)
    invalidateQueue()
  }

  const handleCancel = async (id: number) => {
    await api.cancelOp(id)
    invalidateQueue()
  }

  return (
    <Drawer
      anchor="bottom"
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          maxHeight: '50vh',
          borderTopLeftRadius: 8,
          borderTopRightRadius: 8,
        },
      }}
    >
      <Box sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Operation Queue</Typography>
          <IconButton onClick={onClose} size="small" aria-label="close queue panel">
            <CloseIcon />
          </IconButton>
        </Box>

        {operations.length === 0 && (
          <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No operations in queue
          </Typography>
        )}

        {active.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Active
            </Typography>
            <List dense disablePadding>
              {active.map((op) => (
                <ListItem key={op.id} sx={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Chip label={op.type} size="small" color="primary" sx={{ mr: 1 }} />
                      <Typography variant="body2" component="span">
                        {op.message}
                      </Typography>
                    </Box>
                  </Box>
                  <LinearProgress variant="determinate" value={op.progress} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {failed.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="error" gutterBottom>
              Failed
            </Typography>
            <List dense disablePadding>
              {failed.map((op) => (
                <ListItem key={op.id} sx={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Chip label={op.type} size="small" color="error" sx={{ mr: 1 }} />
                      <Typography variant="body2" component="span" color="error">
                        {op.error}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, ml: 1 }}>
                      <Tooltip title="Re-run this failed operation from the beginning.">
                        <Button
                          size="small"
                          variant="outlined"
                          color="primary"
                          onClick={() => handleRetry(op.id)}
                        >
                          Retry
                        </Button>
                      </Tooltip>
                      <Tooltip title="Mark this operation as skipped and continue with the next one in the queue.">
                        <Button
                          size="small"
                          variant="outlined"
                          color="warning"
                          onClick={() => handleSkip(op.id)}
                        >
                          Skip
                        </Button>
                      </Tooltip>
                    </Box>
                  </Box>
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {pending.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Pending
            </Typography>
            <List dense disablePadding>
              {pending.map((op) => (
                <ListItem key={op.id} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Box>
                    <Chip label={op.type} size="small" sx={{ mr: 1 }} />
                  </Box>
                  <Tooltip title="Remove this operation from the queue before it starts.">
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      onClick={() => handleCancel(op.id)}
                    >
                      Cancel
                    </Button>
                  </Tooltip>
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {completed.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" color="success.main" gutterBottom>
              Completed
            </Typography>
            <List dense disablePadding>
              {completed.map((op) => (
                <ListItem key={op.id}>
                  <CheckIcon color="success" sx={{ mr: 1, fontSize: 18 }} />
                  <Chip label={op.type} size="small" color="success" sx={{ mr: 1 }} />
                </ListItem>
              ))}
            </List>
          </Box>
        )}
      </Box>
    </Drawer>
  )
}
