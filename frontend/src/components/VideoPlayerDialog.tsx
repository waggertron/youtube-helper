import { Dialog, DialogTitle, DialogContent, IconButton, Box } from '@mui/material'
import { Close } from '@mui/icons-material'

interface VideoPlayerDialogProps {
  videoId: string | null
  onClose: () => void
}

export default function VideoPlayerDialog({ videoId, onClose }: VideoPlayerDialogProps) {
  return (
    <Dialog
      open={videoId !== null}
      onClose={onClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Video Player
        <IconButton aria-label="Close player" onClick={onClose} size="small">
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {videoId && (
          <Box sx={{ position: 'relative', paddingTop: '56.25%', width: '100%' }}>
            <iframe
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
              title="YouTube video player"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                border: 'none',
              }}
            />
          </Box>
        )}
      </DialogContent>
    </Dialog>
  )
}
