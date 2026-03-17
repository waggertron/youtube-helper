import { useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useToast } from '../components/ToastProvider'

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
  const toast = useToast()
  return useMutation({
    mutationFn: api.sync,
    onMutate: () => toast.info('Sync started...'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-status'] })
      qc.invalidateQueries({ queryKey: ['playlists'] })
    },
    onError: (err: Error) => toast.error(`Sync failed: ${err.message}`),
  })
}

export const useExportWL = () => {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: api.exportWatchLater,
    onMutate: () => toast.info('Exporting Watch Later videos...'),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['watch-later'] })
      toast.success(`Export complete: ${data.exported} videos exported`)
    },
    onError: (err: Error) => toast.error(`Export failed: ${err.message}`),
  })
}

export const usePurgeWL = () => {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: api.purgeWatchLater,
    onMutate: () => toast.info('Purge started — Chrome will open shortly...'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['purge-status'] })
      qc.invalidateQueries({ queryKey: ['watch-later'] })
    },
    onError: (err: Error) => toast.error(`Purge failed: ${err.message}`),
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
  const toast = useToast()
  return useMutation({
    mutationFn: (playlistId: string) => api.likeAllPlaylist(playlistId),
    onMutate: () => toast.info('Liking all videos...'),
    onSuccess: (_data, playlistId) => {
      qc.invalidateQueries({ queryKey: ['liked-videos'] })
      qc.invalidateQueries({ queryKey: ['playlist', playlistId] })
      toast.success('All videos liked')
    },
    onError: (err: Error) => toast.error(`Like all failed: ${err.message}`),
  })
}

export function useResetDatabase() {
  const qc = useQueryClient()
  const toast = useToast()
  return useMutation({
    mutationFn: () => api.resetDatabase(),
    onSuccess: () => {
      qc.invalidateQueries()
      toast.success('Database reset')
    },
    onError: (err: Error) => toast.error(`Reset failed: ${err.message}`),
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
  const toast = useToast()
  return useMutation({
    mutationFn: (file: File) => api.importWatchLater(file),
    onMutate: () => toast.info('Importing Watch Later videos...'),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['watch-later'] })
      toast.success(`Imported ${data.imported} videos`)
    },
    onError: (err: Error) => toast.error(`Import failed: ${err.message}`),
  })
}

// Status hooks with toast notifications for background task transitions
export function useSyncStatusWithToast() {
  const query = useSyncStatus()
  const toast = useToast()
  const prevStatus = useRef<string | undefined>()

  useEffect(() => {
    const current = query.data?.status
    const prev = prevStatus.current
    if (prev === 'running' && current === 'completed') {
      toast.success(`Sync complete: ${query.data?.message || ''}`)
    } else if (prev === 'running' && current === 'failed') {
      toast.error(`Sync failed: ${query.data?.error || 'Unknown error'}`)
    }
    prevStatus.current = current
  }, [query.data?.status, query.data?.message, query.data?.error, toast])

  return query
}

export function usePurgeStatusWithToast() {
  const query = usePurgeStatus()
  const toast = useToast()
  const prevStatus = useRef<string | undefined>()

  useEffect(() => {
    const current = query.data?.status
    const prev = prevStatus.current
    if (prev === 'running' && current === 'completed') {
      toast.success(`Purge complete: ${query.data?.message || ''}`)
    } else if (prev === 'running' && current === 'failed') {
      toast.error(`Purge failed: ${query.data?.error || 'Unknown error'}`)
    }
    prevStatus.current = current
  }, [query.data?.status, query.data?.message, query.data?.error, toast])

  return query
}
