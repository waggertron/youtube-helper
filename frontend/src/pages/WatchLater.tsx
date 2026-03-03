import { useState } from 'react'
import {
  Box,
  Button,
  Slider,
  Tooltip,
  Typography,
} from '@mui/material'
import VideoTable from '../components/VideoTable'
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

  const handlePruneExports = () => {
    pruneExports.mutate()
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Watch Later
      </Typography>

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
            onClick={handlePruneExports}
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

      <VideoTable videos={videos} />

      <ConfirmDialog
        open={confirmExport}
        title="Confirm Export"
        description={`Export Watch Later videos with a ${threshold}% watch threshold. This will create a dated playlist and use API quota proportional to the number of videos.`}
        onConfirm={handleExportConfirm}
        onCancel={() => setConfirmExport(false)}
      />

      <ConfirmDialog
        open={confirmPurge}
        title="Confirm Purge"
        description={`Purge videos watched above ${threshold}% from your Watch Later playlist. This opens Chrome and removes videos automatically.`}
        onConfirm={handlePurgeConfirm}
        onCancel={() => setConfirmPurge(false)}
      />
    </Box>
  )
}
