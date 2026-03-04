import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export const usePlaylists = () =>
  useQuery({ queryKey: ['playlists'], queryFn: api.listPlaylists })

export const usePlaylistVideos = (id: string) =>
  useQuery({
    queryKey: ['playlist', id],
    queryFn: () => api.getPlaylistVideos(id),
  })

export const useWatchLater = () =>
  useQuery({ queryKey: ['watch-later'], queryFn: api.watchLater })

export const useWatchLaterWatched = (threshold: number) =>
  useQuery({
    queryKey: ['watch-later-watched', threshold],
    queryFn: () => api.watchLaterWatched(threshold),
  })

export const useWatchLaterUnwatched = (threshold: number) =>
  useQuery({
    queryKey: ['watch-later-unwatched', threshold],
    queryFn: () => api.watchLaterUnwatched(threshold),
  })

export const useLikedVideos = () =>
  useQuery({ queryKey: ['liked-videos'], queryFn: api.likedVideos })

export const useSearch = (q: string, threshold?: number) =>
  useQuery({
    queryKey: ['search', q, threshold],
    queryFn: () => api.search(q, threshold),
    enabled: q.length > 0,
  })

export const useAuthStatus = () =>
  useQuery({ queryKey: ['auth-status'], queryFn: api.authStatus })

export const useQueue = () =>
  useQuery({
    queryKey: ['queue'],
    queryFn: api.listQueue,
    refetchInterval: 2000,
  })

export const useAllVideos = () =>
  useQuery({ queryKey: ['all-videos'], queryFn: api.listAllVideos })

// Mutations
export const useSync = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.sync,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const useScrape = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.scrapeWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const useExportWL = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.exportWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const usePurgeWL = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.purgeWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export const usePruneExports = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.pruneExports,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['queue'] }),
  })
}

export function useUploadSecret() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => api.uploadSecret(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['auth-status'] }),
  })
}

export function useStartAuth() {
  return useMutation({
    mutationFn: () => api.startAuth(),
  })
}

export function useLikeAll() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (playlistId: string) => api.likeAllPlaylist(playlistId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['queue'] })
    },
  })
}
