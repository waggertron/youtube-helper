import { useState } from 'react'
import { Box, Typography } from '@mui/material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import VideoTable from '../components/VideoTable'
import ViewModeToggle, { type ViewMode } from '../components/ViewModeToggle'
import VideoPlayerDialog from '../components/VideoPlayerDialog'
import ConfirmDialog from '../components/ConfirmDialog'
import { useLikedVideos } from '../hooks/useApi'
import { api } from '../api/client'
import type { Video } from '../api/client'

export default function LikedVideos() {
  const { data } = useLikedVideos()
  const qc = useQueryClient()
  const [unlikeVideo, setUnlikeVideo] = useState<Video | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('compact')
  const [playingVideo, setPlayingVideo] = useState<string | null>(null)

  const unlike = useMutation({
    mutationFn: (videoId: string) => api.unlikeVideo(videoId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['liked-videos'] }),
  })

  const videos = data?.videos ?? []

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Liked Videos</Typography>
        <ViewModeToggle value={viewMode} onChange={setViewMode} />
      </Box>

      <VideoTable
        videos={videos}
        viewMode={viewMode}
        onRemove={(videoId) => {
          const video = videos.find(v => v.id === videoId)
          if (video) setUnlikeVideo(video)
        }}
        onPlay={(videoId) => setPlayingVideo(videoId)}
      />

      <ConfirmDialog
        open={unlikeVideo !== null}
        title="Unlike Video"
        description={`Unlike "${unlikeVideo?.title}"? This will remove it from your Liked Videos on YouTube.`}
        onConfirm={() => {
          if (unlikeVideo) unlike.mutate(unlikeVideo.id)
          setUnlikeVideo(null)
        }}
        onCancel={() => setUnlikeVideo(null)}
      />

      <VideoPlayerDialog videoId={playingVideo} onClose={() => setPlayingVideo(null)} />
    </Box>
  )
}
