import { ThemeProvider, CssBaseline } from '@mui/material'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import theme from './theme'
import { ToastProvider } from './components/ToastProvider'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Playlists from './pages/Playlists'
import PlaylistDetail from './pages/PlaylistDetail'
import WatchLater from './pages/WatchLater'
import Search from './pages/Search'
import LikedVideos from './pages/LikedVideos'
import AllVideos from './pages/AllVideos'
import Settings from './pages/Settings'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/playlists" element={<Playlists />} />
                <Route path="/playlists/:id" element={<PlaylistDetail />} />
                <Route path="/watch-later" element={<WatchLater />} />
                <Route path="/search" element={<Search />} />
                <Route path="/videos" element={<AllVideos />} />
                <Route path="/liked" element={<LikedVideos />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
