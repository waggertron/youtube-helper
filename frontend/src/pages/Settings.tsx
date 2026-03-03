import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Tooltip,
  Typography,
} from '@mui/material'
import { useAuthStatus, useSync } from '../hooks/useApi'

export default function Settings() {
  const { data } = useAuthStatus()
  const sync = useSync()

  const authenticated = data?.authenticated ?? false

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Authentication
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Shows whether you have valid YouTube API credentials. If
            unauthenticated, run <code>yt auth setup</code> in your terminal to
            configure OAuth.
          </Typography>
          {authenticated ? (
            <Chip label="Authenticated" color="success" />
          ) : (
            <Alert severity="warning">
              Not authenticated. Run <code>yt auth setup</code> in your terminal
              to configure OAuth credentials.
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Sync
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Sync pulls metadata for all your YouTube playlists into the local
            database. Run this periodically to keep your data up to date.
          </Typography>
          <Tooltip title="Sync all playlist metadata from YouTube into the local database. Uses API quota proportional to the number of playlists and videos.">
            <Button
              variant="contained"
              onClick={() => sync.mutate()}
              disabled={sync.isPending}
            >
              Sync Now
            </Button>
          </Tooltip>
        </CardContent>
      </Card>
    </Box>
  )
}
