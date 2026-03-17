import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export const usePlaylists = () =>
  useQuery({ queryKey: ['playlists'], queryFn: api.listPlaylists, staleTime: 10_000 })

export const usePlaylistVideos = (id: string) =>
  useQuery({
    queryKey: ['playlist', id],
    queryFn: () => api.getPlaylistVideos(id),
    staleTime: 10_000,
  })

export const useWatchLater = () =>
  useQuery({ queryKey: ['watch-later'], queryFn: api.watchLater, staleTime: 10_000 })

export const useWatchLaterWatched = (threshold: number) =>
  useQuery({
    queryKey: ['watch-later-watched', threshold],
    queryFn: () => api.watchLaterWatched(threshold),
    staleTime: 10_000,
  })

export const useWatchLaterUnwatched = (threshold: number) =>
  useQuery({
    queryKey: ['watch-later-unwatched', threshold],
    queryFn: () => api.watchLaterUnwatched(threshold),
    staleTime: 10_000,
  })

export const useLikedVideos = () =>
  useQuery({ queryKey: ['liked-videos'], queryFn: api.likedVideos, staleTime: 10_000 })

export const useSearch = (q: string, threshold?: number) =>
  useQuery({
    queryKey: ['search', q, threshold],
    queryFn: () => api.search(q, threshold),
    enabled: q.length > 0,
    staleTime: 5_000,
  })

export const useAuthStatus = () =>
  useQuery({ queryKey: ['auth-status'], queryFn: api.authStatus, staleTime: 30_000 })

export const useAllVideos = () =>
  useQuery({ queryKey: ['all-videos'], queryFn: api.listAllVideos, staleTime: 30_000 })

// Mutations
export const useSync = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.sync,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-status'] })
      qc.invalidateQueries({ queryKey: ['playlists'] })
    },
  })
}

export const useExportWL = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.exportWatchLater,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watch-later'] }),
  })
}

export const usePurgeWL = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: api.purgeWatchLater,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purge-status'] })
      qc.invalidateQueries({ queryKey: ['watch-later'] })
    },
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
    onSuccess: (_data, playlistId) => {
      qc.invalidateQueries({ queryKey: ['liked-videos'] })
      qc.invalidateQueries({ queryKey: ['playlist', playlistId] })
    },
  })
}

export function useResetDatabase() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.resetDatabase(),
    onSuccess: () => {
      qc.invalidateQueries()
    },
  })
}

export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync-status'],
    queryFn: () => api.syncStatus(),
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.status === 'running' ? 2000 : false
    },
  })
}

export function usePurgeStatus() {
  return useQuery({
    queryKey: ['purge-status'],
    queryFn: () => api.purgeStatus(),
    refetchInterval: (query) => {
      const data = query.state.data
      return data?.status === 'running' ? 2000 : false
    },
  })
}

export function useImportWatchLater() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => api.importWatchLater(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watch-later'] }),
  })
}
