import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  AppBar, Toolbar, Typography, IconButton, Badge,
} from '@mui/material'
import {
  Dashboard as DashboardIcon,
  PlaylistPlay,
  WatchLater,
  Search as SearchIcon,
  VideoLibrary,
  ThumbUp,
  Settings,
  Menu as MenuIcon,
  Queue as QueueIcon,
} from '@mui/icons-material'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useQueue } from '../hooks/useApi'
import { useSSE } from '../hooks/useSSE'
import QueuePanel from './QueuePanel'

const DRAWER_WIDTH = 240

const NAV_ITEMS = [
  { label: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { label: 'Playlists', icon: <PlaylistPlay />, path: '/playlists' },
  { label: 'Watch Later', icon: <WatchLater />, path: '/watch-later' },
  { label: 'Search', icon: <SearchIcon />, path: '/search' },
  { label: 'All Videos', icon: <VideoLibrary />, path: '/videos' },
  { label: 'Liked Videos', icon: <ThumbUp />, path: '/liked' },
  { label: 'Settings', icon: <Settings />, path: '/settings' },
]

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [queueOpen, setQueueOpen] = useState(false)
  const qc = useQueryClient()
  const { data } = useQueue()
  const operations = data?.operations ?? []
  const activeCount = operations.filter(
    (op) => op.status === 'active' || op.status === 'pending',
  ).length

  // Wire SSE events to instantly refresh queue data
  useSSE((event) => {
    if (event.type === 'queue') {
      qc.invalidateQueries({ queryKey: ['queue'] })
      // Also refresh data that operations may have changed
      if (event.status === 'completed') {
        qc.invalidateQueries({ queryKey: ['playlists'] })
        qc.invalidateQueries({ queryKey: ['watch-later'] })
        qc.invalidateQueries({ queryKey: ['liked-videos'] })
        qc.invalidateQueries({ queryKey: ['all-videos'] })
      }
    }
  })

  const drawer = (
    <Box>
      <Toolbar>
        <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          YT Helper
        </Typography>
      </Toolbar>
      <List>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => { navigate(item.path); setMobileOpen(false) }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            aria-label="open navigation menu"
            color="inherit"
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            YouTube Helper
          </Typography>
          <IconButton
            aria-label="open queue panel"
            color="inherit"
            onClick={() => setQueueOpen(!queueOpen)}
          >
            <Badge badgeContent={activeCount} color="error">
              <QueueIcon />
            </Badge>
          </IconButton>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {drawer}
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Outlet />
      </Box>
      <QueuePanel
        operations={operations}
        open={queueOpen}
        onClose={() => setQueueOpen(false)}
      />
    </Box>
  )
}
