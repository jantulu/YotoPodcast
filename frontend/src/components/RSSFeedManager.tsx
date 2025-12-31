import { useState } from 'react'

interface Episode {
  title: string
  description: string
  audio_url: string
  published: string
  duration: string
}

interface Feed {
  title: string
  description: string
  episodes: Episode[]
}

interface RSSFeedManagerProps {
  accessToken: string
  onEpisodeUploaded: () => void
}

export default function RSSFeedManager({ accessToken, onEpisodeUploaded }: RSSFeedManagerProps) {
  const [feedUrl, setFeedUrl] = useState('https://rss.wbur.org/circleround/podcast')
  const [feed, setFeed] = useState<Feed | null>(null)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState<string | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  const fetchFeed = async () => {
    setLoading(true)
    setMessage(null)
    try {
      const response = await fetch(
        `/api/rss/feeds/parse?feed_url=${encodeURIComponent(feedUrl)}`
      )
      if (!response.ok) throw new Error('Failed to fetch feed')
      const data = await response.json()
      setFeed(data.feed)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to load feed' })
    } finally {
      setLoading(false)
    }
  }

  const uploadEpisode = async (episode: Episode, playlistCardId?: string) => {
    setUploading(episode.audio_url)
    setMessage(null)
    
    try {
      const formData = new FormData()
      formData.append('audio_url', episode.audio_url)
      formData.append('title', episode.title)
      formData.append('access_token', accessToken)
      if (playlistCardId) {
        formData.append('playlist_card_id', playlistCardId)
      }

      const response = await fetch('/api/rss/feeds/upload-episode', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Upload failed')
      
      setMessage({ type: 'success', text: 'Episode uploaded successfully!' })
      onEpisodeUploaded()
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Upload failed' })
    } finally {
      setUploading(null)
    }
  }

  return (
    <div className="form-container">
      <h2>RSS Podcast Feed</h2>
      
      {message && (
        <div className={message.type === 'success' ? 'success-message' : 'error-message'}>
          {message.text}
        </div>
      )}

      <div className="form-group">
        <label>RSS Feed URL:</label>
        <div style={{ display: 'flex', gap: '10px' }}>
          <input
            type="text"
            value={feedUrl}
            onChange={(e) => setFeedUrl(e.target.value)}
            placeholder="Enter RSS feed URL"
            style={{ flex: 1 }}
          />
          <button 
            onClick={fetchFeed}
            disabled={loading || !feedUrl}
            className="submit-btn"
            style={{ width: 'auto', padding: '12px 30px' }}
          >
            {loading ? 'Loading...' : 'Load Feed'}
          </button>
        </div>
      </div>

      {feed && (
        <div className="feed-info">
          <h3>{feed.title}</h3>
          <p>{feed.description}</p>
          
          <div className="episodes-list">
            <h4>Episodes ({feed.episodes.length})</h4>
            {feed.episodes.map((episode, index) => (
              <div key={index} className="episode-item">
                <div className="episode-info">
                  <h5>{episode.title}</h5>
                  <p className="episode-meta">
                    {episode.published && new Date(episode.published).toLocaleDateString()}
                    {episode.duration && ` • ${episode.duration}`}
                  </p>
                  <p className="episode-description">
                    {episode.description.substring(0, 200)}
                    {episode.description.length > 200 && '...'}
                  </p>
                </div>
                <button
                  onClick={() => uploadEpisode(episode)}
                  disabled={uploading === episode.audio_url || !episode.audio_url}
                  className="btn-upload"
                >
                  {uploading === episode.audio_url ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}