import { useState, useMemo } from 'react'
import {
  Box, TextField, FormControl, InputLabel, Select, MenuItem,
  InputAdornment,
} from '@mui/material'
import { Search } from '@mui/icons-material'
import type { Video } from '../api/client'

type SortField = 'title' | 'channel_name' | 'duration' | 'watch_progress'
type SortDir = 'asc' | 'desc'
type LikedFilter = 'all' | 'liked' | 'not-liked'

interface VideoFiltersProps {
  videos: Video[]
  showLikedFilter?: boolean
  children: (filtered: Video[]) => React.ReactNode
}

export default function VideoFilters({ videos, showLikedFilter = false, children }: VideoFiltersProps) {
  const [search, setSearch] = useState('')
  const [sortField, setSortField] = useState<SortField>('title')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [likedFilter, setLikedFilter] = useState<LikedFilter>('all')

  const filtered = useMemo(() => {
    let result = [...videos]

    // Text filter
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(
        v => v.title.toLowerCase().includes(q) || v.channel_name.toLowerCase().includes(q)
      )
    }

    // Liked filter
    if (likedFilter === 'liked') {
      result = result.filter(v => v.is_liked)
    } else if (likedFilter === 'not-liked') {
      result = result.filter(v => !v.is_liked)
    }

    // Sort
    result.sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'title':
          cmp = a.title.localeCompare(b.title)
          break
        case 'channel_name':
          cmp = a.channel_name.localeCompare(b.channel_name)
          break
        case 'duration':
          cmp = a.duration - b.duration
          break
        case 'watch_progress':
          cmp = a.watch_progress - b.watch_progress
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })

    return result
  }, [videos, search, sortField, sortDir, likedFilter])

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder="Filter by title or channel..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <Search fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
          sx={{ minWidth: 250 }}
        />
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel>Sort by</InputLabel>
          <Select
            value={sortField}
            label="Sort by"
            onChange={(e) => setSortField(e.target.value as SortField)}
          >
            <MenuItem value="title">Title</MenuItem>
            <MenuItem value="channel_name">Channel</MenuItem>
            <MenuItem value="duration">Duration</MenuItem>
            <MenuItem value="watch_progress">Progress</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 100 }}>
          <InputLabel>Order</InputLabel>
          <Select
            value={sortDir}
            label="Order"
            onChange={(e) => setSortDir(e.target.value as SortDir)}
          >
            <MenuItem value="asc">Asc</MenuItem>
            <MenuItem value="desc">Desc</MenuItem>
          </Select>
        </FormControl>
        {showLikedFilter && (
          <FormControl size="small" sx={{ minWidth: 130 }}>
            <InputLabel>Liked</InputLabel>
            <Select
              value={likedFilter}
              label="Liked"
              onChange={(e) => setLikedFilter(e.target.value as LikedFilter)}
            >
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="liked">Liked only</MenuItem>
              <MenuItem value="not-liked">Not liked</MenuItem>
            </Select>
          </FormControl>
        )}
      </Box>
      {children(filtered)}
    </Box>
  )
}
