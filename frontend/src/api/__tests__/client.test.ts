import { describe, it, expect } from 'vitest'
import { api } from '../client'

describe('API client', () => {
  it('fetches health endpoint', async () => {
    const data = await api.health()
    expect(data.status).toBe('ok')
    expect(data.version).toBe('0.1.0')
  })

  it('fetches playlists', async () => {
    const data = await api.listPlaylists()
    expect(data.playlists).toEqual([])
  })

  it('fetches auth status', async () => {
    const data = await api.authStatus()
    expect(data).toHaveProperty('authenticated')
    expect(data.authenticated).toBe(false)
    expect(data.has_client_secret).toBe(false)
    expect(data.has_token).toBe(false)
  })

  it('submits sync operation', async () => {
    const data = await api.sync()
    expect(data.operation_id).toBe(1)
    expect(data.message).toBe('Sync queued')
  })

  it('searches with query', async () => {
    const data = await api.search('test')
    expect(data.query).toBe('test')
    expect(data.results).toEqual([])
  })

  it('fetches watch later videos', async () => {
    const data = await api.watchLater()
    expect(data.videos).toEqual([])
  })

  it('fetches liked videos', async () => {
    const data = await api.likedVideos()
    expect(data.videos).toEqual([])
  })

  it('fetches queue operations', async () => {
    const data = await api.listQueue()
    expect(data.operations).toEqual([])
  })

  it('throws on HTTP error', async () => {
    // MSW doesn't have a handler for this specific endpoint, so it will fail
    await expect(api.getPlaylistVideos('nonexistent')).rejects.toThrow()
  })
})
