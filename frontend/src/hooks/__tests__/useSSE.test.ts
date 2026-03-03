import { describe, it, expect } from 'vitest'

// Test the hook logic conceptually - EventSource is not available in jsdom
// So we test the module exports and type structure
describe('useSSE', () => {
  it('module exports useSSE function', async () => {
    const mod = await import('../useSSE')
    expect(typeof mod.useSSE).toBe('function')
  })
})
