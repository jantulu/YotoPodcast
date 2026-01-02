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
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0 })
  const [playlistName, setPlaylistName] = useState('')
  const [useExistingPlaylist, setUseExistingPlaylist] = useState(false)
  const [existingPlaylists, setExistingPlaylists] = useState<any[]>([])
  const [selectedPlaylistId, setSelectedPlaylistId] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [pendingEpisodes, setPendingEpisodes] = useState<Episode[] | null>(null)

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

  const performUpload = async (episodes: Episode[]) => {
    setUploading(true)
    setMessage(null)
    setUploadProgress({ current: 0, total: episodes.length })
    let successCount = 0
    let failCount = 0
    let currentPlaylistId = useExistingPlaylist ? selectedPlaylistId : null

    console.log(`Starting upload of ${episodes.length} episodes`)
    console.log(`Using existing playlist: ${useExistingPlaylist}`)
    console.log(`Current playlist ID: ${currentPlaylistId}`)
    console.log(`Playlist name: ${playlistName}`)

    for (let i = 0; i < episodes.length; i++) {
      const episode = episodes[i]
      setUploadProgress({ current: i + 1, total: episodes.length })
      console.log(`\n--- Uploading episode ${i + 1}/${episodes.length}: ${episode.title} ---`)
      
      try {
        const formData = new FormData()
        formData.append('audio_url', episode.audio_url)
        formData.append('title', episode.title)
        formData.append('access_token', accessToken)
        
        if (currentPlaylistId) {
          console.log(`Adding to existing playlist: ${currentPlaylistId}`)
          formData.append('playlist_card_id', currentPlaylistId)
        } else if (!useExistingPlaylist && playlistName) {
          console.log(`Creating new playlist with name: ${playlistName}`)
          formData.append('playlist_name', playlistName)
        }

        const response = await fetch('/api/rss/feeds/upload-episode', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const errorText = await response.text()
          console.error(`Upload failed: ${errorText}`)
          throw new Error(`Upload failed: ${response.status}`)
        }
        
        const result = await response.json()
        console.log('Upload response:', result)
        
        // Extract playlist ID from response
        const newPlaylistId = result.playlistId || result.cardId
        console.log(`Extracted playlist ID: ${newPlaylistId}`)
        
        // Use the returned playlist ID for subsequent uploads
        if (!currentPlaylistId && newPlaylistId) {
          currentPlaylistId = newPlaylistId
          console.log(`Set current playlist ID to: ${currentPlaylistId}`)
        }
        
        successCount++
        console.log(`✓ Episode ${i + 1} uploaded successfully`)
      } catch (error) {
        console.error(`✗ Failed to upload episode ${i + 1}:`, error)
        failCount++
      }
    }

    setUploading(false)
    setSelectedEpisodes(new Set())
    
    if (failCount === 0) {
      setMessage({ type: 'success', text: `Successfully uploaded ${successCount} episode(s) to playlist!` })
    } else {
      setMessage({ type: 'error', text: `Uploaded ${successCount}, failed ${failCount}` })
    }
    
    loadExistingPlaylists()
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

    // Build list of episodes to upload and deduplicate by audio_url
    let episodes = currentFeed?.episodes.filter((e: Episode) => selectedEpisodes.has(e.audio_url)) || []
    const seen = new Set<string>()
    episodes = episodes.filter(e => {
      if (seen.has(e.audio_url)) return false
      seen.add(e.audio_url)
      return true
    })

    console.log('uploadSelected: uploading episodes (titles):', episodes.map(e => e.title))
    console.log('uploadSelected: uploading episodes (audio_urls):', episodes.map(e => e.audio_url))
    // Confirm with user before starting
    const playlistLabel = useExistingPlaylist
      ? `Existing playlist: ${playlistName} (ID: ${selectedPlaylistId})`
      : `New playlist: ${playlistName}`

    const confirmList = episodes.map(e => `- ${e.title}`).join('\n')
    const confirmText = `Upload ${episodes.length} episode(s) to ${playlistLabel}?\n\n${confirmList}`

    if (!window.confirm(confirmText)) {
      setMessage({ type: 'error', text: 'Upload cancelled by user' })
      return
    }

    setUploading(true)
    setMessage(null)
    setUploadProgress({ current: 0, total: episodes.length })
    let successCount = 0
    let failCount = 0
    let currentPlaylistId = useExistingPlaylist ? selectedPlaylistId : null

    console.log(`Starting upload of ${episodes.length} episodes`)
    console.log(`Using existing playlist: ${useExistingPlaylist}`)
    console.log(`Current playlist ID: ${currentPlaylistId}`)
    console.log(`Playlist name: ${playlistName}`)

    for (let i = 0; i < episodes.length; i++) {
      const episode = episodes[i]
      setUploadProgress({ current: i + 1, total: episodes.length })
      console.log(`\n--- Uploading episode ${i + 1}/${episodes.length}: ${episode.title} ---`)
      
      try {
        const formData = new FormData()
        formData.append('audio_url', episode.audio_url)
        formData.append('title', episode.title)
        formData.append('access_token', accessToken)
        
        if (currentPlaylistId) {
          console.log(`Adding to existing playlist: ${currentPlaylistId}`)
          formData.append('playlist_card_id', currentPlaylistId)
        } else if (!useExistingPlaylist && playlistName) {
          console.log(`Creating new playlist with name: ${playlistName}`)
          formData.append('playlist_name', playlistName)
        }

        const response = await fetch('/api/rss/feeds/upload-episode', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const errorText = await response.text()
          console.error(`Upload failed: ${errorText}`)
          throw new Error(`Upload failed: ${response.status}`)
        }
        
        const result = await response.json()
        console.log('Upload response:', result)
        
        // Extract playlist ID from response
        const newPlaylistId = result.playlistId || result.cardId
        console.log(`Extracted playlist ID: ${newPlaylistId}`)
        
        // Use the returned playlist ID for subsequent uploads
        if (!currentPlaylistId && newPlaylistId) {
          // Build list of episodes to upload and deduplicate by audio_url
          let episodes = currentFeed?.episodes.filter((e: Episode) => selectedEpisodes.has(e.audio_url)) || []
          const seen = new Set<string>()
          episodes = episodes.filter((e: Episode) => {
            if (seen.has(e.audio_url)) return false
            seen.add(e.audio_url)
            return true
          })

          console.log('uploadSelected: uploading episodes (titles):', episodes.map(e => e.title))
          console.log('uploadSelected: uploading episodes (audio_urls):', episodes.map(e => e.audio_url))

          // Open confirmation modal with pending episodes
          setPendingEpisodes(episodes)
          setConfirmOpen(true)
        }

        const confirmUpload = async (confirm: boolean) => {
          if (!confirm) {
            setConfirmOpen(false)
            setPendingEpisodes(null)
            setMessage({ type: 'error', text: 'Upload cancelled by user' })
            return
          }

          if (pendingEpisodes) {
            setConfirmOpen(false)
            const eps = pendingEpisodes
            setPendingEpisodes(null)
            await performUpload(eps)
          }
        }

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

                  <input
                    type="text"
                    placeholder="Enter playlist name"
                    value={playlistName}
                    onChange={(e) => setPlaylistName(e.target.value)}
                    className="playlist-input"
                    disabled={useExistingPlaylist}
                  />
                  {useExistingPlaylist && (
                    <select
                      value={selectedPlaylistId}
                      onChange={(e) => {
                        const val = e.target.value
                        setSelectedPlaylistId(val)
                        setUseExistingPlaylist(true)
                        const found = existingPlaylists.find((p: any) => p.cardId === val)
                        if (found) setPlaylistName(found.title || '')
                      }}
                      className="playlist-select"
                    >
                      <option value="">-- Select Playlist --</option>
                      {existingPlaylists.map((p: any) => (
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
                    {uploading 
                      ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...` 
                      : `Upload ${selectedEpisodes.size} Episode(s)`
                    }
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
      {confirmOpen && (
        <div style={{position: 'fixed', left:0,top:0,right:0,bottom:0,background:'rgba(0,0,0,0.5)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:9999}}>
          <div style={{background:'#fff',padding:20,borderRadius:8,maxWidth:600,width:'90%'}}>
            <h3>Confirm Upload</h3>
            <p>{useExistingPlaylist ? `Existing playlist: ${playlistName} (ID: ${selectedPlaylistId})` : `New playlist: ${playlistName}`}</p>
            <div style={{maxHeight:200,overflow:'auto',marginBottom:12}}>
              <ul>
                {pendingEpisodes && pendingEpisodes.map((e, i) => (
                  <li key={i}>{e.title}</li>
                ))}
              </ul>
            </div>
            <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
              <button onClick={() => confirmUpload(false)} style={{padding:'8px 12px'}}>Cancel</button>
              <button onClick={() => confirmUpload(true)} style={{padding:'8px 12px'}}>Confirm</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}