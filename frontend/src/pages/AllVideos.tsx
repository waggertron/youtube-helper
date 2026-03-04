import { useState } from 'react'
import { Box, Typography, Chip } from '@mui/material'
import { useAllVideos } from '../hooks/useApi'
import { api } from '../api/client'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import VideoTable from '../components/VideoTable'
import VideoFilters from '../components/VideoFilters'
import ViewModeToggle, { type ViewMode } from '../components/ViewModeToggle'
import VideoPlayerDialog from '../components/VideoPlayerDialog'
import type { VideoWithPlaylists } from '../api/client'

export default function AllVideos() {
  const { data } = useAllVideos()
  const videos = (data?.videos ?? []) as VideoWithPlaylists[]
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [playingVideo, setPlayingVideo] = useState<string | null>(null)
  const qc = useQueryClient()

  const likeMutation = useMutation({
    mutationFn: (videoId: string) => api.likeVideo(videoId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['all-videos'] })
      qc.invalidateQueries({ queryKey: ['liked-videos'] })
    },
  })

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">All Videos</Typography>
        <ViewModeToggle value={viewMode} onChange={setViewMode} />
      </Box>

      <VideoFilters videos={videos} showLikedFilter>
        {(filtered) => (
          <VideoTable
            videos={filtered}
            viewMode={viewMode}
            onLike={(videoId) => likeMutation.mutate(videoId)}
            onPlay={(videoId) => setPlayingVideo(videoId)}
            extraColumns={(video) => {
              const v = video as VideoWithPlaylists
              if (!v.playlist_names) return null
              return (
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {v.playlist_names.split(',').map((name) => (
                    <Chip key={name} label={name} size="small" variant="outlined" />
                  ))}
                </Box>
              )
            }}
          />
        )}
      </VideoFilters>

      <VideoPlayerDialog videoId={playingVideo} onClose={() => setPlayingVideo(null)} />
    </Box>
  )
}
