import { useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Tooltip,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material'
import { Delete, Add } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { usePlaylists } from '../hooks/useApi'
import { api } from '../api/client'
import ConfirmDialog from '../components/ConfirmDialog'

export default function Playlists() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data } = usePlaylists()
  const playlists = data?.playlists ?? []

  const [createOpen, setCreateOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [deleteId, setDeleteId] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: (title: string) => api.createPlaylist({ title, privacy: 'private' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
      setCreateOpen(false)
      setNewTitle('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deletePlaylist(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['playlists'] })
      setDeleteId(null)
    },
  })

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Playlists</Typography>
        <Tooltip title="Create a new private playlist on your YouTube account. This uses 50 API quota units.">
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateOpen(true)}
          >
            Create Playlist
          </Button>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        {playlists.map((playlist) => (
          <Grid key={playlist.id} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card
              sx={{ cursor: 'pointer', '&:hover': { boxShadow: 4 } }}
              onClick={() => navigate(`/playlists/${playlist.id}`)}
            >
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {playlist.title}
                </Typography>
                <Typography color="text.secondary" gutterBottom>
                  {playlist.video_count} videos
                </Typography>
                <Chip label={playlist.privacy_status} size="small" />
              </CardContent>
              <CardActions>
                <Tooltip title="Permanently delete this playlist from YouTube. All videos in the playlist will be unlinked but not deleted from YouTube. This cannot be undone.">
                  <IconButton
                    aria-label="Delete playlist"
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleteId(playlist.id)
                    }}
                  >
                    <Delete fontSize="small" />
                  </IconButton>
                </Tooltip>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create Playlist Dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)}>
        <DialogTitle>Create New Playlist</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Playlist Title"
            fullWidth
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button
            onClick={() => createMutation.mutate(newTitle)}
            variant="contained"
            disabled={!newTitle.trim() || createMutation.isPending}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <ConfirmDialog
        open={deleteId !== null}
        title="Delete Playlist"
        description={(() => {
          const playlistToDelete = playlists.find(p => p.id === deleteId)
          return `Permanently delete "${playlistToDelete?.title}" and its ${playlistToDelete?.video_count ?? 0} videos from YouTube. This cannot be undone.`
        })()}
        onConfirm={() => {
          if (deleteId) deleteMutation.mutate(deleteId)
        }}
        onCancel={() => setDeleteId(null)}
      />
    </Box>
  )
}
