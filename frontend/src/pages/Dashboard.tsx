import {
  Box, Card, CardContent, Typography, Grid, Button, Tooltip, Chip, Stack,
} from '@mui/material'
import { Sync, WatchLater, PlaylistPlay, VideoLibrary } from '@mui/icons-material'
import { usePlaylists, useWatchLater, useSync, useScrape, useQueue } from '../hooks/useApi'

export default function Dashboard() {
  const { data: playlistData } = usePlaylists()
  const { data: wlData } = useWatchLater()
  const { data: queueData } = useQueue()
  const syncMutation = useSync()
  const scrapeMutation = useScrape()

  const playlists = playlistData?.playlists ?? []
  const wlVideos = wlData?.videos ?? []
  const queue = queueData?.operations ?? []
  const activeOps = queue.filter(op => op.status === 'active')
  const pendingOps = queue.filter(op => op.status === 'pending')
  const totalVideos = playlists.reduce((sum, p) => sum + (p.video_count || 0), 0)

  const cards = [
    { label: 'Playlists', value: playlists.length, icon: <PlaylistPlay fontSize="large" /> },
    { label: 'Total Videos', value: totalVideos, icon: <VideoLibrary fontSize="large" /> },
    { label: 'Watch Later', value: wlVideos.length, icon: <WatchLater fontSize="large" /> },
  ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Dashboard</Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        {cards.map((card) => (
          <Grid key={card.label} size={{ xs: 12, sm: 4 }}>
            <Card>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {card.icon}
                <Box>
                  <Typography variant="h4" fontWeight="bold">{card.value}</Typography>
                  <Typography color="text.secondary">{card.label}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Typography variant="h5" gutterBottom>Quick Actions</Typography>
      <Stack direction="row" spacing={2} sx={{ mb: 4 }}>
        <Tooltip title="Pull all playlist and video metadata from YouTube into your local database. This fetches metadata only — no video files are downloaded. Uses YouTube Data API quota (1 unit per page).">
          <span>
            <Button
              variant="contained"
              startIcon={<Sync />}
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
            >
              Sync Playlists
            </Button>
          </span>
        </Tooltip>
        <Tooltip title="Launch Chrome using your logged-in profile to scroll through your Watch Later playlist and extract video metadata plus watch progress from the thumbnail progress bars. Uses zero API quota.">
          <span>
            <Button
              variant="contained"
              color="secondary"
              startIcon={<WatchLater />}
              onClick={() => scrapeMutation.mutate()}
              disabled={scrapeMutation.isPending}
            >
              Scrape Watch Later
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {(activeOps.length > 0 || pendingOps.length > 0) && (
        <Box>
          <Typography variant="h5" gutterBottom>Queue Status</Typography>
          {activeOps.map(op => (
            <Chip
              key={op.id}
              label={`${op.type}: ${op.message || 'Running...'} (${op.progress.toFixed(0)}%)`}
              color="primary"
              sx={{ mr: 1 }}
            />
          ))}
          {pendingOps.length > 0 && (
            <Chip label={`${pendingOps.length} pending`} variant="outlined" />
          )}
        </Box>
      )}
    </Box>
  )
}
