import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper,
  IconButton, Tooltip, Box, Card, CardMedia, CardContent, CardActions,
  Typography, Chip, Link, Grid,
} from '@mui/material'
import { Delete, ThumbUp, PlayArrow, Download } from '@mui/icons-material'
import type { Video } from '../api/client'
import type { ViewMode } from './ViewModeToggle'

interface VideoTableProps {
  videos: Video[]
  viewMode?: ViewMode
  onRemove?: (videoId: string) => void
  onLike?: (videoId: string) => void
  onPlay?: (videoId: string) => void
  extraColumns?: (video: Video) => React.ReactNode
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function youtubeUrl(videoId: string): string {
  return `https://www.youtube.com/watch?v=${videoId}`
}

function downloadUrl(videoId: string): string {
  return `https://www.cobalt.tools/?u=${encodeURIComponent(youtubeUrl(videoId))}`
}

function thumbnailSrc(video: Video): string {
  return video.thumbnail_url || `https://i.ytimg.com/vi/${video.id}/mqdefault.jpg`
}

function LikedIndicator({ isLiked }: { isLiked?: number | null }) {
  if (!isLiked) return null
  return (
    <Tooltip title="Liked">
      <ThumbUp fontSize="small" color="primary" sx={{ ml: 0.5, verticalAlign: 'middle' }} />
    </Tooltip>
  )
}

function ActionButtons({ video, onRemove, onLike, onPlay }: {
  video: Video
  onRemove?: (id: string) => void
  onLike?: (id: string) => void
  onPlay?: (id: string) => void
}) {
  return (
    <>
      {onPlay && (
        <Tooltip title="Play in browser">
          <IconButton aria-label="Play" size="small" onClick={() => onPlay(video.id)}>
            <PlayArrow fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
      <Tooltip title="Download video">
        <IconButton
          aria-label="Download"
          size="small"
          component="a"
          href={downloadUrl(video.id)}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Download fontSize="small" />
        </IconButton>
      </Tooltip>
      {onRemove && (
        <Tooltip title="Remove this video from the playlist. The video itself is not deleted from YouTube.">
          <IconButton aria-label="Remove" size="small" onClick={() => onRemove(video.id)}>
            <Delete fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
      {onLike && (
        <Tooltip title={video.is_liked ? "Already liked" : "Add this video to your YouTube Liked Videos. Uses 50 API quota units."}>
          <span>
            <IconButton
              aria-label="Like"
              size="small"
              onClick={() => onLike(video.id)}
              disabled={!!video.is_liked}
            >
              <ThumbUp fontSize="small" color={video.is_liked ? "primary" : "inherit"} />
            </IconButton>
          </span>
        </Tooltip>
      )}
    </>
  )
}

function GridView({ videos, onRemove, onLike, onPlay, extraColumns }: Omit<VideoTableProps, 'viewMode'>) {
  return (
    <Grid container spacing={2}>
      {videos.map((video) => (
        <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={video.id}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Link href={youtubeUrl(video.id)} target="_blank" rel="noopener noreferrer">
              <CardMedia
                component="img"
                height="180"
                image={thumbnailSrc(video)}
                alt={video.title}
                sx={{ objectFit: 'cover' }}
              />
            </Link>
            <CardContent sx={{ flexGrow: 1, pb: 0 }}>
              <Link
                href={youtubeUrl(video.id)}
                target="_blank"
                rel="noopener noreferrer"
                underline="hover"
                color="inherit"
              >
                <Typography variant="subtitle2" sx={{
                  overflow: 'hidden', textOverflow: 'ellipsis',
                  display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
                }}>
                  {video.title}
                </Typography>
              </Link>
              <Typography variant="caption" color="text.secondary">
                {video.channel_name}
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5, alignItems: 'center', flexWrap: 'wrap' }}>
                <Chip label={formatDuration(video.duration)} size="small" variant="outlined" />
                {video.watch_progress > 0 && (
                  <Chip label={`${video.watch_progress}%`} size="small" color="info" variant="outlined" />
                )}
                <LikedIndicator isLiked={video.is_liked} />
              </Box>
              {extraColumns && <Box sx={{ mt: 0.5 }}>{extraColumns(video)}</Box>}
            </CardContent>
            <CardActions>
              <ActionButtons video={video} onRemove={onRemove} onLike={onLike} onPlay={onPlay} />
            </CardActions>
          </Card>
        </Grid>
      ))}
    </Grid>
  )
}

function ListView({ videos, onRemove, onLike, onPlay, extraColumns }: Omit<VideoTableProps, 'viewMode'>) {
  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: 168 }}>Thumbnail</TableCell>
            <TableCell>Title</TableCell>
            <TableCell>Channel</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell>Progress</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {videos.map((video) => (
            <TableRow key={video.id}>
              <TableCell sx={{ p: 0.5 }}>
                <Link href={youtubeUrl(video.id)} target="_blank" rel="noopener noreferrer">
                  <Box
                    component="img"
                    src={thumbnailSrc(video)}
                    alt={video.title}
                    sx={{ width: 160, height: 90, objectFit: 'cover', borderRadius: 1 }}
                  />
                </Link>
              </TableCell>
              <TableCell>
                <Link
                  href={youtubeUrl(video.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  underline="hover"
                  color="inherit"
                >
                  {video.title}
                </Link>
                <LikedIndicator isLiked={video.is_liked} />
                {extraColumns && <Box sx={{ mt: 0.5 }}>{extraColumns(video)}</Box>}
              </TableCell>
              <TableCell>{video.channel_name}</TableCell>
              <TableCell>{formatDuration(video.duration)}</TableCell>
              <TableCell>{video.watch_progress > 0 ? `${video.watch_progress}%` : ''}</TableCell>
              <TableCell>
                <ActionButtons video={video} onRemove={onRemove} onLike={onLike} onPlay={onPlay} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function CompactView({ videos, onRemove, onLike, onPlay, extraColumns }: Omit<VideoTableProps, 'viewMode'>) {
  return (
    <TableContainer component={Paper}>
      <Table size="small">
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
              <TableCell>
                <Link
                  href={youtubeUrl(video.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  underline="hover"
                  color="inherit"
                >
                  {video.title}
                </Link>
                <LikedIndicator isLiked={video.is_liked} />
                {extraColumns && <Box sx={{ mt: 0.5 }}>{extraColumns(video)}</Box>}
              </TableCell>
              <TableCell>{video.channel_name}</TableCell>
              <TableCell>{formatDuration(video.duration)}</TableCell>
              <TableCell>{video.watch_progress > 0 ? `${video.watch_progress}%` : ''}</TableCell>
              <TableCell>
                <ActionButtons video={video} onRemove={onRemove} onLike={onLike} onPlay={onPlay} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default function VideoTable({ videos, viewMode = 'compact', onRemove, onLike, onPlay, extraColumns }: VideoTableProps) {
  switch (viewMode) {
    case 'grid':
      return <GridView videos={videos} onRemove={onRemove} onLike={onLike} onPlay={onPlay} extraColumns={extraColumns} />
    case 'list':
      return <ListView videos={videos} onRemove={onRemove} onLike={onLike} onPlay={onPlay} extraColumns={extraColumns} />
    case 'compact':
    default:
      return <CompactView videos={videos} onRemove={onRemove} onLike={onLike} onPlay={onPlay} extraColumns={extraColumns} />
  }
}
