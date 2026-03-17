import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { usePlaylists, useAuthStatus, useWatchLater, useLikedVideos } from '../useApi'

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('React Query hooks', () => {
  it('usePlaylists returns playlist data', async () => {
    const { result } = renderHook(() => usePlaylists(), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.playlists).toEqual([])
  })

  it('useAuthStatus returns auth data', async () => {
    const { result } = renderHook(() => useAuthStatus(), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.authenticated).toBe(false)
  })

  it('useWatchLater returns watch later data', async () => {
    const { result } = renderHook(() => useWatchLater(), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.videos).toEqual([])
  })

  it('useLikedVideos returns liked video data', async () => {
    const { result } = renderHook(() => useLikedVideos(), {
      wrapper: createWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.videos).toEqual([])
  })
})
