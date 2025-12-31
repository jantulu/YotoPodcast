import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { Playlist } from '../types'

interface UploadFormProps {
  accessToken: string
}

export default function UploadForm({ accessToken }: UploadFormProps) {
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [selectedPlaylist, setSelectedPlaylist] = useState<string>('')
  const [createNew, setCreateNew] = useState(false)
  const [title, setTitle] = useState('')
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    fetchPlaylists()
  }, [accessToken])

  const fetchPlaylists = async () => {
    try {
      const data = await api.playlists.getAll(accessToken)
      setPlaylists(data || [])
    } catch (error) {
      console.error('Failed to fetch playlists:', error)
      setPlaylists([])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!audioFile || !title) return

    setUploading(true)
    setMessage(null)

    try {
      const result = await api.upload(
        audioFile,
        title,
        accessToken,
        createNew ? undefined : selectedPlaylist
      )

      setMessage({ type: 'success', text: result.message })
      setTitle('')
      setAudioFile(null)
      fetchPlaylists()
      
      const fileInput = document.getElementById('audio-file') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Upload failed' })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="form-container">
      <h2>Upload Podcast Episode</h2>
      
      {message && (
        <div className={message.type === 'success' ? 'success-message' : 'error-message'}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="radio-group">
          <label>
            <input
              type="radio"
              checked={!createNew}
              onChange={() => setCreateNew(false)}
            />
            Add to existing playlist
          </label>
          <label>
            <input
              type="radio"
              checked={createNew}
              onChange={() => setCreateNew(true)}
            />
            Create new playlist
          </label>
        </div>

        {!createNew && (
          <div className="form-group">
            <label>Select Playlist:</label>
            <select
              value={selectedPlaylist}
              onChange={(e) => setSelectedPlaylist(e.target.value)}
              required={!createNew}
            >
              <option value="">-- Select Playlist --</option>
              {playlists && playlists.map((playlist) => (
                <option key={playlist.cardId} value={playlist.cardId}>
                  {playlist.title}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="form-group">
          <label>Episode Title:</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter episode title"
            required
          />
        </div>

        <div className="form-group">
          <label>Audio File:</label>
          <input
            id="audio-file"
            type="file"
            accept="audio/*"
            onChange={(e) => setAudioFile(e.target.files?.[0] || null)}
            required
          />
        </div>

        <button type="submit" disabled={uploading} className="submit-btn">
          {uploading ? 'Uploading...' : 'Upload Podcast'}
        </button>
      </form>
    </div>
  )
}