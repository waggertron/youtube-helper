import { useState } from 'react'
import { Box, Typography, IconButton, Tooltip, Button } from '@mui/material'
import { ArrowBack, FavoriteRounded } from '@mui/icons-material'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usePlaylistVideos, useLikeAll } from '../hooks/useApi'
import { api } from '../api/client'
import type { Video } from '../api/client'
import VideoTable from '../components/VideoTable'
import VideoFilters from '../components/VideoFilters'
import ViewModeToggle, { type ViewMode } from '../components/ViewModeToggle'
import VideoPlayerDialog from '../components/VideoPlayerDialog'
import ConfirmDialog from '../components/ConfirmDialog'

export default function PlaylistDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data } = usePlaylistVideos(id!)
  const [removeVideo, setRemoveVideo] = useState<Video | null>(null)
  const [confirmLikeAll, setConfirmLikeAll] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('compact')
  const [playingVideo, setPlayingVideo] = useState<string | null>(null)

  const playlist = data?.playlist
  const videos = data?.videos ?? []
  const unlikedCount = videos.filter(v => !v.is_liked).length

  const removeMutation = useMutation({
    mutationFn: (videoId: string) => api.removeVideo(id!, videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playlist', id] })
    },
  })

  const likeMutation = useMutation({
    mutationFn: (videoId: string) => api.likeVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['liked-videos'] })
      queryClient.invalidateQueries({ queryKey: ['playlist', id] })
    },
  })

  const likeAll = useLikeAll()

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Tooltip title="Back to playlists">
          <IconButton
            aria-label="Back to playlists"
            onClick={() => navigate('/playlists')}
          >
            <ArrowBack />
          </IconButton>
        </Tooltip>
        <Typography variant="h4" sx={{ flexGrow: 1 }}>
          {playlist?.title ?? 'Loading...'}
        </Typography>
        <Button
          variant="outlined"
          startIcon={<FavoriteRounded />}
          onClick={() => setConfirmLikeAll(true)}
          disabled={unlikedCount === 0 || likeAll.isPending}
        >
          Like All
        </Button>
        <ViewModeToggle value={viewMode} onChange={setViewMode} />
      </Box>

      <VideoFilters videos={videos} showLikedFilter>
        {(filtered) => (
          <VideoTable
            videos={filtered}
            viewMode={viewMode}
            onRemove={(videoId) => {
              const video = videos.find(v => v.id === videoId)
              if (video) setRemoveVideo(video)
            }}
            onLike={(videoId) => likeMutation.mutate(videoId)}
            onPlay={(videoId) => setPlayingVideo(videoId)}
          />
        )}
      </VideoFilters>

      <ConfirmDialog
        open={removeVideo !== null}
        title="Remove Video"
        description={`Remove "${removeVideo?.title}" from "${playlist?.title}"?`}
        onConfirm={() => {
          if (removeVideo) removeMutation.mutate(removeVideo.id)
          setRemoveVideo(null)
        }}
        onCancel={() => setRemoveVideo(null)}
      />

      <ConfirmDialog
        open={confirmLikeAll}
        title="Like All Videos"
        description={`Like ${unlikedCount} unliked video${unlikedCount !== 1 ? 's' : ''} in "${playlist?.title}"? This uses 50 API quota units per video.`}
        onConfirm={() => {
          likeAll.mutate(id!)
          setConfirmLikeAll(false)
        }}
        onCancel={() => setConfirmLikeAll(false)}
      />

      <VideoPlayerDialog videoId={playingVideo} onClose={() => setPlayingVideo(null)} />
    </Box>
  )
}
