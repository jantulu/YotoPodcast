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

const safeGetStorage = (key: string) => {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

const safeSetStorage = (key: string, value: string) => {
  try {
    localStorage.setItem(key, value)
  } catch {
    // iOS Safari private mode / quota issues
  }
}

export default function PodcastManager({ accessToken }: PodcastManagerProps) {
  const [savedFeeds, setSavedFeeds] = useState<SavedFeed[]>([])
  const [newFeedName, setNewFeedName] = useState('')
  const [newFeedUrl, setNewFeedUrl] = useState('https://rss.wbur.org/circleround/podcast')
  const [selectedFeedId, setSelectedFeedId] = useState<string>('')
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

  useEffect(() => {
    requestAnimationFrame(loadSavedFeeds)
    loadExistingPlaylists()
  }, [])

  const loadSavedFeeds = () => {
    const saved = safeGetStorage(STORAGE_KEY)
    if (saved) {
      setSavedFeeds(JSON.parse(saved))
    }
  }

  const loadExistingPlaylists = async () => {
    try {
      const response = await fetch(`/api/playlists?access_token=${accessToken}`)
      const data = await response.json()
      setExistingPlaylists(data.playlists || [])
    } catch (error) {
      console.error('Failed to load playlists:', error)
    }
  }

  const saveFeed = () => {
    if (!newFeedName || !newFeedUrl) return

    const newFeed: SavedFeed = {
      id: Date.now().toString(),
      name: newFeedName,
      url: newFeedUrl,
    }

    const updated = [...savedFeeds, newFeed]
    setSavedFeeds(updated)
    safeSetStorage(STORAGE_KEY, JSON.stringify(updated))
    setNewFeedName('')
    setNewFeedUrl('')
  }

  const deleteFeed = (id: string) => {
    const updated = savedFeeds.filter(f => f.id !== id)
    setSavedFeeds(updated)
    safeSetStorage(STORAGE_KEY, JSON.stringify(updated))

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
      const response = await fetch(
        `/api/rss/feeds/parse?feed_url=${encodeURIComponent(feed.url)}`
      )
      if (!response.ok) throw new Error('Failed to load feed')

      const data = await response.json()
      setCurrentFeed(data.feed)

      if (!playlistName) {
        setPlaylistName(data.feed.title)
      }
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to load feed' })
      setCurrentFeed(null)
    } finally {
      setLoading(false)
    }
  }

  const toggleEpisode = (audioUrl: string) => {
    const next = new Set(selectedEpisodes)
    next.has(audioUrl) ? next.delete(audioUrl) : next.add(audioUrl)
    setSelectedEpisodes(next)
  }

  const selectAll = () => {
    if (!currentFeed) return
    const urls = new Set(getFilteredEpisodes().map(e => e.audio_url))
    setSelectedEpisodes(urls)
  }

  const deselectAll = () => {
    setSelectedEpisodes(new Set())
  }

  const uploadSelected = async () => {
    if (selectedEpisodes.size === 0) {
      setMessage({ type: 'error', text: 'Please select at least one episode' })
      return
    }

    if (!useExistingPlaylist && !playlistName) {
      setMessage({ type: 'error', text: 'Please enter a playlist name' })
      return
    }

    if (useExistingPlaylist && !selectedPlaylistId) {
      setMessage({ type: 'error', text: 'Please select a playlist' })
      return
    }

    const episodes = currentFeed?.episodes.filter(e =>
      selectedEpisodes.has(e.audio_url)
    ) || []

    setUploading(true)
    setUploadProgress({ current: 0, total: episodes.length })

    let currentPlaylistId = useExistingPlaylist ? selectedPlaylistId : null

    for (let i = 0; i < episodes.length; i++) {
      const episode = episodes[i]
      setUploadProgress({ current: i + 1, total: episodes.length })

      try {
        const formData = new FormData()
        formData.append('audio_url', episode.audio_url)
        formData.append('title', episode.title)
        formData.append('access_token', accessToken)

        if (currentPlaylistId) {
          formData.append('playlist_card_id', currentPlaylistId)
        } else if (!useExistingPlaylist && playlistName) {
          formData.append('playlist_name', playlistName)
        }

        const response = await fetch('/api/rss/feeds/upload-episode', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.status}`)
        }

        const result = await response.json()
        const newPlaylistId = result.playlistId || result.cardId
        if (!currentPlaylistId && newPlaylistId) {
          currentPlaylistId = newPlaylistId
        }
      } catch (error) {
        console.error('Upload failed', error)
      }
    }

    setUploading(false)
    setSelectedEpisodes(new Set())
    loadExistingPlaylists()
  }

  const getFilteredEpisodes = () => {
    if (!currentFeed) return []
    if (!searchTerm) return currentFeed.episodes

    const term = searchTerm.toLowerCase()
    return currentFeed.episodes.filter(e =>
      e.title.toLowerCase().includes(term) ||
      e.description.toLowerCase().includes(term)
    )
  }

  const filteredEpisodes = getFilteredEpisodes()

  return (
    <div className="podcast-manager">
      <div className="manager-layout">

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
              className="btn-add-feed"
              onClick={(e) => {
                e.stopPropagation()
                saveFeed()
              }}
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
                  onClick={(e) => {
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

        <div className="main-content">
          {!currentFeed ? (
            <div className="empty-state">
              Select a podcast feed from the sidebar
            </div>
          ) : (
            <>
              <div className="episodes-header">
                <input
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  placeholder="Search episodes..."
                />
                <button type="button" onClick={selectAll}>Select All</button>
                <button type="button" onClick={deselectAll}>Deselect All</button>
              </div>

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
            </>
          )}
        </div>

      </div>
    </div>
  )
}
