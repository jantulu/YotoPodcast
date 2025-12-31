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

export default function PodcastManager({ accessToken }: PodcastManagerProps) {
  const [savedFeeds, setSavedFeeds] = useState<SavedFeed[]>([])
  const [newFeedName, setNewFeedName] = useState('')
  const [newFeedUrl, setNewFeedUrl] = useState('https://rss.wbur.org/circleround/podcast')
  const [selectedFeedId, setSelectedFeedId] = useState<string>('')
  const [currentFeed, setCurrentFeed] = useState<Feed | null>(null)
  const [selectedEpisodes, setSelectedEpisodes] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [playlistName, setPlaylistName] = useState('')
  const [useExistingPlaylist, setUseExistingPlaylist] = useState(false)
  const [existingPlaylists, setExistingPlaylists] = useState<any[]>([])
  const [selectedPlaylistId, setSelectedPlaylistId] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadSavedFeeds()
    loadExistingPlaylists()
  }, [])

  const loadSavedFeeds = () => {
    const saved = localStorage.getItem('saved_podcast_feeds')
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
      url: newFeedUrl
    }
    
    const updated = [...savedFeeds, newFeed]
    setSavedFeeds(updated)
    localStorage.setItem('saved_podcast_feeds', JSON.stringify(updated))
    setNewFeedName('')
    setNewFeedUrl('')
  }

  const deleteFeed = (id: string) => {
    const updated = savedFeeds.filter(f => f.id !== id)
    setSavedFeeds(updated)
    localStorage.setItem('saved_podcast_feeds', JSON.stringify(updated))
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
    const newSelected = new Set(selectedEpisodes)
    if (newSelected.has(audioUrl)) {
      newSelected.delete(audioUrl)
    } else {
      newSelected.add(audioUrl)
    }
    setSelectedEpisodes(newSelected)
  }

  const selectAll = () => {
    if (!currentFeed) return
    const filtered = getFilteredEpisodes()
    const allUrls = new Set(filtered.map(e => e.audio_url))
    setSelectedEpisodes(allUrls)
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

    setUploading(true)
    setMessage(null)

    const episodes = currentFeed?.episodes.filter(e => selectedEpisodes.has(e.audio_url)) || []
    let successCount = 0
    let failCount = 0
    let currentPlaylistId = useExistingPlaylist ? selectedPlaylistId : null

    for (const episode of episodes) {
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

        if (!response.ok) throw new Error('Upload failed')
        
        const result = await response.json()
        
        // Use the returned playlist ID for subsequent uploads
        if (!currentPlaylistId && result.cardId) {
          currentPlaylistId = result.cardId
        }
        
        successCount++
      } catch (error) {
        console.error(`Failed to upload ${episode.title}:`, error)
        failCount++
      }
    }

    setUploading(false)
    setSelectedEpisodes(new Set())
    
    if (failCount === 0) {
      setMessage({ type: 'success', text: `Successfully uploaded ${successCount} episode(s)!` })
    } else {
      setMessage({ type: 'error', text: `Uploaded ${successCount}, failed ${failCount}` })
    }
    
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
        {/* Left Sidebar - Saved Feeds */}
        <div className="feeds-sidebar">
          <h3>Podcast Feeds</h3>
          
          <div className="add-feed-form">
            <input
              type="text"
              placeholder="Feed name"
              value={newFeedName}
              onChange={(e) => setNewFeedName(e.target.value)}
              className="feed-input"
            />
            <input
              type="text"
              placeholder="RSS URL"
              value={newFeedUrl}
              onChange={(e) => setNewFeedUrl(e.target.value)}
              className="feed-input"
            />
            <button onClick={saveFeed} className="btn-add-feed">
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
                  <span className="feed-name">{feed.name}</span>
                </div>
                <button 
                  onClick={() => deleteFeed(feed.id)}
                  className="btn-delete-feed"
                  title="Delete feed"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="main-content">
          {message && (
            <div className={message.type === 'success' ? 'success-message' : 'error-message'}>
              {message.text}
            </div>
          )}

          {!currentFeed ? (
            <div className="empty-state">
              <p>Select a podcast feed from the sidebar to view episodes</p>
            </div>
          ) : (
            <>
              {/* Upload Controls */}
              <div className="upload-controls">
                <div className="playlist-selection">
                  <div className="radio-group-inline">
                    <label>
                      <input
                        type="radio"
                        checked={!useExistingPlaylist}
                        onChange={() => setUseExistingPlaylist(false)}
                      />
                      New Playlist
                    </label>
                    <label>
                      <input
                        type="radio"
                        checked={useExistingPlaylist}
                        onChange={() => setUseExistingPlaylist(true)}
                      />
                      Existing Playlist
                    </label>
                  </div>

                  {!useExistingPlaylist ? (
                    <input
                      type="text"
                      placeholder="Enter playlist name"
                      value={playlistName}
                      onChange={(e) => setPlaylistName(e.target.value)}
                      className="playlist-input"
                    />
                  ) : (
                    <select
                      value={selectedPlaylistId}
                      onChange={(e) => setSelectedPlaylistId(e.target.value)}
                      className="playlist-select"
                    >
                      <option value="">-- Select Playlist --</option>
                      {existingPlaylists.map(p => (
                        <option key={p.cardId} value={p.cardId}>
                          {p.title}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="upload-actions">
                  <span className="selected-count">
                    {selectedEpisodes.size} selected
                  </span>
                  <button 
                    onClick={uploadSelected}
                    disabled={uploading || selectedEpisodes.size === 0}
                    className="btn-upload-selected"
                  >
                    {uploading ? 'Uploading...' : `Upload ${selectedEpisodes.size} Episode(s)`}
                  </button>
                </div>
              </div>

              {/* Episodes List */}
              <div className="episodes-section">
                <div className="episodes-header">
                  <h3>{currentFeed.title}</h3>
                  <div className="episodes-controls">
                    <input
                      type="text"
                      placeholder="Search episodes..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="search-input"
                    />
                    <button onClick={selectAll} className="btn-select">
                      Select All
                    </button>
                    <button onClick={deselectAll} className="btn-select">
                      Deselect All
                    </button>
                  </div>
                </div>

                <div className="episodes-list-compact">
                  {loading ? (
                    <div className="loading-state">Loading episodes...</div>
                  ) : filteredEpisodes.length === 0 ? (
                    <div className="empty-state">No episodes found</div>
                  ) : (
                    filteredEpisodes.map((episode, index) => (
                      <div 
                        key={index} 
                        className={`episode-compact ${selectedEpisodes.has(episode.audio_url) ? 'selected' : ''}`}
                        onClick={() => toggleEpisode(episode.audio_url)}
                      >
                        <input
                          type="checkbox"
                          checked={selectedEpisodes.has(episode.audio_url)}
                          onChange={() => {}}
                          className="episode-checkbox"
                        />
                        <div className="episode-content">
                          <span className="episode-title">{episode.title}</span>
                          <span className="episode-meta">
                            {episode.published && new Date(episode.published).toLocaleDateString()}
                            {episode.duration && ` • ${episode.duration}`}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right Sidebar - Playlists */}
        <div className="playlists-sidebar">
          <h3>Your Playlists</h3>
          <div className="playlists-list-compact">
            {existingPlaylists.length === 0 ? (
              <div className="empty-state-small">No playlists yet</div>
            ) : (
              existingPlaylists.map(playlist => (
                <div key={playlist.cardId} className="playlist-compact">
                  <span className="playlist-title">{playlist.title}</span>
                  <span className="playlist-id">{playlist.cardId}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}