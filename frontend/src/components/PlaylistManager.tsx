import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { Playlist } from '../types'

interface PlaylistManagerProps {
  accessToken: string
}

export default function PlaylistManager({ accessToken }: PlaylistManagerProps) {
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPlaylists()
  }, [accessToken])

  const fetchPlaylists = async () => {
    try {
      setLoading(true)
      const data = await api.playlists.getAll(accessToken)
      setPlaylists(data)
    } catch (error) {
      console.error('Failed to fetch playlists:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (cardId: string) => {
    if (!confirm('Are you sure you want to delete this playlist?')) return

    try {
      await api.playlists.delete(cardId, accessToken)
      setPlaylists(playlists.filter(p => p.cardId !== cardId))
    } catch (error) {
      alert('Failed to delete playlist')
      console.error('Delete error:', error)
    }
  }

  const handleView = async (cardId: string) => {
    try {
      const playlist = await api.playlists.getById(cardId, accessToken)
      alert(JSON.stringify(playlist, null, 2))
    } catch (error) {
      alert('Failed to load playlist details')
      console.error('View error:', error)
    }
  }

  if (loading) {
    return <div className="form-container">Loading playlists...</div>
  }

  return (
    <div className="form-container">
      <h2>Your Playlists ({playlists.length})</h2>
      
      {playlists.length === 0 ? (
        <div className="empty-state">
          No playlists yet. Upload your first podcast above!
        </div>
      ) : (
        <div className="playlist-list">
          {playlists.map((playlist) => (
            <div key={playlist.cardId} className="playlist-item">
              <div className="playlist-info">
                <h3>{playlist.title}</h3>
                <p>Card ID: {playlist.cardId}</p>
              </div>
              <div className="playlist-actions">
                <button 
                  onClick={() => handleView(playlist.cardId)}
                  className="btn-view"
                >
                  View
                </button>
                <button 
                  onClick={() => handleDelete(playlist.cardId)}
                  className="btn-delete"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}