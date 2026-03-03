import { Box, Typography } from '@mui/material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import VideoTable from '../components/VideoTable'
import { useLikedVideos } from '../hooks/useApi'
import { api } from '../api/client'

export default function LikedVideos() {
  const { data } = useLikedVideos()
  const qc = useQueryClient()

  const unlike = useMutation({
    mutationFn: (videoId: string) => api.unlikeVideo(videoId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['liked-videos'] }),
  })

  const videos = data?.videos ?? []

  const handleUnlike = (videoId: string) => {
    unlike.mutate(videoId)
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Liked Videos
      </Typography>

      <VideoTable videos={videos} onRemove={handleUnlike} />
    </Box>
  )
}
