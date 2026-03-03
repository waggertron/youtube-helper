import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../test/render'
import Layout from '../Layout'

describe('Layout', () => {
  it('renders the sidebar with navigation items', () => {
    renderWithProviders(<Layout />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Playlists')).toBeInTheDocument()
    expect(screen.getByText('Watch Later')).toBeInTheDocument()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('Liked Videos')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders the app title', () => {
    renderWithProviders(<Layout />)
    expect(screen.getByText('YouTube Helper')).toBeInTheDocument()
  })
})
