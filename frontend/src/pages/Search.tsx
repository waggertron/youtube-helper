import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Chip,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useSearch } from '../hooks/useApi'

export default function Search() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  const { data } = useSearch(debouncedQuery)

  const results = data?.results ?? []
  const videoResults = results.filter((r) => r.type === 'video')
  const playlistResults = results.filter((r) => r.type === 'playlist')
  const hasSearched = debouncedQuery.length > 0
  const noResults = hasSearched && results.length === 0

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search
      </Typography>

      <Tooltip title="Search uses fuzzy matching across all video titles, channel names, and playlist names in your local database. Higher threshold = stricter matching. No API quota used.">
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2, cursor: 'help' }}>
          Search uses fuzzy matching across your local database. No API quota used.
        </Typography>
      </Tooltip>

      <TextField
        fullWidth
        placeholder="Search videos and playlists..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        sx={{ mb: 3 }}
      />

      {noResults && (
        <Typography color="text.secondary">
          No results found for &quot;{debouncedQuery}&quot;
        </Typography>
      )}

      {videoResults.length > 0 && (
        <Paper sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ p: 2, pb: 0 }}>
            Videos
          </Typography>
          <List>
            {videoResults.map((result) => (
              <ListItemButton key={result.id}>
                <ListItemText
                  primary={result.title}
                  secondary={result.channel_name}
                />
                <Chip label={String(result.score)} size="small" />
              </ListItemButton>
            ))}
          </List>
        </Paper>
      )}

      {playlistResults.length > 0 && (
        <Paper sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ p: 2, pb: 0 }}>
            Playlists
          </Typography>
          <List>
            {playlistResults.map((result) => (
              <ListItemButton
                key={result.id}
                onClick={() => navigate(`/playlists/${result.id}`)}
              >
                <ListItemText
                  primary={result.title}
                  secondary={
                    result.video_count != null
                      ? `${result.video_count} videos`
                      : undefined
                  }
                />
                <Chip label={String(result.score)} size="small" />
              </ListItemButton>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  )
}
