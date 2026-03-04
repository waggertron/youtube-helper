import { useState } from 'react'
import {
  Box,
  Button,
  Slider,
  Tooltip,
  Typography,
} from '@mui/material'
import VideoTable from '../components/VideoTable'
import VideoFilters from '../components/VideoFilters'
import ViewModeToggle, { type ViewMode } from '../components/ViewModeToggle'
import VideoPlayerDialog from '../components/VideoPlayerDialog'
import ConfirmDialog from '../components/ConfirmDialog'
import {
  useWatchLater,
  useScrape,
  useExportWL,
  usePurgeWL,
  usePruneExports,
} from '../hooks/useApi'

export default function WatchLater() {
  const [threshold, setThreshold] = useState(80)
  const [confirmExport, setConfirmExport] = useState(false)
  const [confirmPurge, setConfirmPurge] = useState(false)
  const [confirmPrune, setConfirmPrune] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('compact')
  const [playingVideo, setPlayingVideo] = useState<string | null>(null)

  const { data } = useWatchLater()
  const scrape = useScrape()
  const exportWL = useExportWL()
  const purgeWL = usePurgeWL()
  const pruneExports = usePruneExports()

  const videos = data?.videos ?? []

  const handleScrape = () => {
    scrape.mutate()
  }

  const handleExportConfirm = () => {
    exportWL.mutate({ target: 'default', threshold })
    setConfirmExport(false)
  }

  const handlePurgeConfirm = () => {
    purgeWL.mutate({ threshold })
    setConfirmPurge(false)
  }

  const watchedCount = videos.filter(v => v.watch_progress >= threshold).length

  const handlePruneConfirm = () => {
    pruneExports.mutate()
    setConfirmPrune(false)
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Watch Later</Typography>
        <ViewModeToggle value={viewMode} onChange={setViewMode} />
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Tooltip title="Launch Chrome to scan your Watch Later playlist. This opens a browser window using your Chrome profile and scrolls through Watch Later to detect video metadata and watch progress from thumbnail progress bars. Uses zero API quota.">
          <Button
            variant="contained"
            onClick={handleScrape}
            disabled={scrape.isPending}
          >
            Scrape
          </Button>
        </Tooltip>

        <Tooltip title="Create a dated private playlist with all Watch Later videos, append to the master archive, copy unwatched videos to your target playlist, and remove watched videos from the local database. This uses API quota proportional to the number of videos (50 units per video added).">
          <Button
            variant="contained"
            onClick={() => setConfirmExport(true)}
            disabled={exportWL.isPending}
          >
            Export
          </Button>
        </Tooltip>

        <Tooltip title="Open Chrome and automatically remove all watched videos from your Watch Later playlist on YouTube. This scrolls through Watch Later, finds videos you've watched above the threshold, and clicks 'Remove from Watch Later' on each. Uses zero API quota.">
          <Button
            variant="contained"
            color="warning"
            onClick={() => setConfirmPurge(true)}
            disabled={purgeWL.isPending}
          >
            Purge
          </Button>
        </Tooltip>

        <Tooltip title="Scan all Watch Later Export playlists and remove videos you've since watched. Helps keep export playlists clean over time. Uses API quota for list + remove operations.">
          <Button
            variant="contained"
            onClick={() => setConfirmPrune(true)}
            disabled={pruneExports.isPending}
          >
            Prune Exports
          </Button>
        </Tooltip>
      </Box>

      <Box sx={{ mb: 3, maxWidth: 400 }}>
        <Typography gutterBottom>
          Threshold: {threshold}%
        </Typography>
        <Slider
          value={threshold}
          onChange={(_e, value) => setThreshold(value as number)}
          min={0}
          max={100}
          valueLabelDisplay="auto"
        />
      </Box>

      <VideoFilters videos={videos}>
        {(filtered) => (
          <VideoTable videos={filtered} viewMode={viewMode} onPlay={(videoId) => setPlayingVideo(videoId)} />
        )}
      </VideoFilters>

      <ConfirmDialog
        open={confirmExport}
        title="Confirm Export"
        description={`Export ${videos.length} Watch Later videos with a ${threshold}% watch threshold. This will create a dated playlist and use API quota proportional to the number of videos.`}
        onConfirm={handleExportConfirm}
        onCancel={() => setConfirmExport(false)}
      />

      <ConfirmDialog
        open={confirmPurge}
        title="Confirm Purge"
        description={`Purge ${watchedCount} video${watchedCount !== 1 ? 's' : ''} watched above ${threshold}% from your Watch Later playlist. This opens Chrome and removes videos automatically.`}
        onConfirm={handlePurgeConfirm}
        onCancel={() => setConfirmPurge(false)}
      />

      <ConfirmDialog
        open={confirmPrune}
        title="Confirm Prune"
        description="Remove watched videos from all Watch Later Export playlists. This scans export playlists and removes videos you've since watched."
        onConfirm={handlePruneConfirm}
        onCancel={() => setConfirmPrune(false)}
      />

      <VideoPlayerDialog videoId={playingVideo} onClose={() => setPlayingVideo(null)} />
    </Box>
  )
}
