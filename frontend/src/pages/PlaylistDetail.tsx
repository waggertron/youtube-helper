import { Box, Typography, IconButton, Tooltip } from '@mui/material'
import { ArrowBack } from '@mui/icons-material'
import { useParams, useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usePlaylistVideos } from '../hooks/useApi'
import { api } from '../api/client'
import VideoTable from '../components/VideoTable'

export default function PlaylistDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data } = usePlaylistVideos(id!)

  const playlist = data?.playlist
  const videos = data?.videos ?? []

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
    },
  })

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
        <Typography variant="h4">
          {playlist?.title ?? 'Loading...'}
        </Typography>
      </Box>

      <VideoTable
        videos={videos}
        onRemove={(videoId) => removeMutation.mutate(videoId)}
        onLike={(videoId) => likeMutation.mutate(videoId)}
      />
    </Box>
  )
}
