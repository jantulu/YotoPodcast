import { useState, useEffect } from 'react'

interface SavedFeed {
  id: string
  name: string
  url: string
}

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

interface PodcastManagerProps {
  accessToken: string
}

const STORAGE_KEY = 'saved_podcast_feeds'

export default function PodcastManager({ accessToken }: PodcastManagerProps) {
  const [savedFeeds, setSavedFeeds] = useState<SavedFeed[]>([])
  const [newFeedName, setNewFeedName] = useState('')
  const [newFeedUrl, setNewFeedUrl] = useState('https://rss.wbur.org/circleround/podcast')
  const [selectedFeedId, setSelectedFeedId] = useState('')
  const [currentFeed, setCurrentFeed] = useState<Feed | null>(null)
  const [selectedEpisodes, setSelectedEpisodes] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 })
  const [playlistName, setPlaylistName] = useState('')
  const [useExistingPlaylist, setUseExistingPlaylist] = useState(false)
  const [existingPlaylists, setExistingPlaylists] = useState<any[]>([])
  const [selectedPlaylistId, setSelectedPlaylistId] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  /* ---------------- storage helpers (mobile safe) ---------------- */

  const loadSavedFeeds = () => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        setSavedFeeds(JSON.parse(raw))
      }
    } catch (err) {
      console.warn('Failed to read localStorage', err)
    }
  }

  const persistFeeds = (feeds: SavedFeed[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(feeds))
    } catch (err) {
      console.warn('Failed to write localStorage', err)
    }
  }

  /* ---------------- initial load ---------------- */

  useEffect(() => {
    requestAnimationFrame(loadSavedFeeds)
    loadExistingPlaylists()
  }, [])

  /* ---------------- playlists ---------------- */

  const loadExistingPlaylists = async () => {
    try {
      const res = await fetch(`/api/playlists?access_token=${accessToken}`)
      const data = await res.json()
      setExistingPlaylists(data.playlists || [])
    } catch (err) {
      console.error('Failed to load playlists', err)
    }
  }

  /* ---------------- feeds ---------------- */

  const saveFeed = () => {
    if (!newFeedName || !newFeedUrl) return

    const newFeed: SavedFeed = {
      id: Date.now().toString(),
      name: newFeedName.trim(),
      url: newFeedUrl.trim(),
    }

    const updated = [...savedFeeds, newFeed]
    setSavedFeeds(updated)
    persistFeeds(updated)

    setNewFeedName('')
    setNewFeedUrl('')
  }

  const deleteFeed = (id: string) => {
    const updated = savedFeeds.filter(f => f.id !== id)
    setSavedFeeds(updated)
    persistFeeds(updated)

    if (selectedFeedId === id) {
      setSelectedFeedId('')
      setCurrentFeed(null)
    }
  }

  const loadFeed = async (feedId: string) => {
    const feed = savedFeeds.find(f => f.id === feedId)
    if (!feed) return

    setLoading(true)
    setMessage(null)
    setSelectedFeedId(feedId)
    setSelectedEpisodes(new Set())

    try {
      const res = await fetch(
        `/api/rss/feeds/parse?feed_url=${encodeURIComponent(feed.url)}`
      )
      if (!res.ok) throw new Error('Failed to load feed')

      const data = await res.json()
      setCurrentFeed(data.feed)
      if (!playlistName) setPlaylistName(data.feed.title)
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to load feed' })
      setCurrentFeed(null)
    } finally {
      setLoading(false)
    }
  }

  /* ---------------- episodes ---------------- */

  const toggleEpisode = (audioUrl: string) => {
    setSelectedEpisodes(prev => {
      const next = new Set(prev)
      next.has(audioUrl) ? next.delete(audioUrl) : next.add(audioUrl)
      return next
    })
  }

  const getFilteredEpisodes = () => {
    if (!currentFeed) return []
    if (!searchTerm) return currentFeed.episodes

    const t = searchTerm.toLowerCase()
    return currentFeed.episodes.filter(e =>
      e.title.toLowerCase().includes(t) ||
      e.description.toLowerCase().includes(t)
    )
  }

  const filteredEpisodes = getFilteredEpisodes()

  /* ---------------- render ---------------- */

  return (
    <div className="podcast-manager">
      <div className="manager-layout">

        {/* -------- Feeds Sidebar -------- */}
        <div className="feeds-sidebar">
          <h3>Podcast Feeds</h3>

          <div className="add-feed-form">
            <input
              value={newFeedName}
              onChange={e => setNewFeedName(e.target.value)}
              placeholder="Feed name"
            />
            <input
              value={newFeedUrl}
              onChange={e => setNewFeedUrl(e.target.value)}
              placeholder="RSS URL"
            />
            <button
              type="button"
              onClick={saveFeed}
              className="btn-add-feed"
            >
              + Add Feed
            </button>
          </div>

          <div className="saved-feeds-list">
            {savedFeeds.map(feed => (
              <div
                key={feed.id}
                className={`feed-item ${selectedFeedId === feed.id ? 'active' : ''}`}
              >
                <div
                  className="feed-info"
                  onClick={() => loadFeed(feed.id)}
                >
                  {feed.name}
                </div>

                <button
                  type="button"
                  className="btn-delete-feed"
                  onClick={e => {
                    e.stopPropagation()
                    deleteFeed(feed.id)
                  }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* -------- Main Content -------- */}
        <div className="main-content">
          {!currentFeed ? (
            <div className="empty-state">Select a feed to view episodes</div>
          ) : (
            <div className="episodes-list-compact">
              {filteredEpisodes.map(ep => (
                <div
                  key={ep.audio_url}
                  className={`episode-compact ${selectedEpisodes.has(ep.audio_url) ? 'selected' : ''}`}
                  onClick={() => toggleEpisode(ep.audio_url)}
                >
                  <input
                    type="checkbox"
                    checked={selectedEpisodes.has(ep.audio_url)}
                    readOnly
                  />
                  <span>{ep.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
