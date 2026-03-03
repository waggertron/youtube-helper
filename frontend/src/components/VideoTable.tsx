import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material'
import { Delete, ThumbUp } from '@mui/icons-material'
import type { Video } from '../api/client'

interface VideoTableProps {
  videos: Video[]
  onRemove?: (videoId: string) => void
  onLike?: (videoId: string) => void
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

export default function VideoTable({ videos, onRemove, onLike }: VideoTableProps) {
  const hasActions = !!onRemove || !!onLike

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Title</TableCell>
            <TableCell>Channel</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell>Progress</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {videos.map((video, index) => (
            <TableRow key={video.id}>
              <TableCell>{index + 1}</TableCell>
              <TableCell>{video.title}</TableCell>
              <TableCell>{video.channel_name}</TableCell>
              <TableCell>{formatDuration(video.duration)}</TableCell>
              <TableCell>{video.watch_progress > 0 ? `${video.watch_progress}%` : ''}</TableCell>
              <TableCell>
                {hasActions && (
                  <>
                    {onRemove && (
                      <Tooltip title="Remove this video from the playlist. The video itself is not deleted from YouTube.">
                        <IconButton
                          aria-label="Remove"
                          size="small"
                          onClick={() => onRemove(video.id)}
                        >
                          <Delete fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {onLike && (
                      <Tooltip title="Add this video to your YouTube Liked Videos. Uses 50 API quota units.">
                        <IconButton
                          aria-label="Like"
                          size="small"
                          onClick={() => onLike(video.id)}
                        >
                          <ThumbUp fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}
