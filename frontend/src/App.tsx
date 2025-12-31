import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './components/Login'
import UploadForm from './components/UploadForm'
import PlaylistManager from './components/PlaylistManager'

function App() {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('yoto_access_token')
    if (token) {
      setAccessToken(token)
    }
    setLoading(false)
  }, [])

  const handleLogin = (token: string) => {
    localStorage.setItem('yoto_access_token', token)
    setAccessToken(token)
  }

  const handleLogout = () => {
    localStorage.removeItem('yoto_access_token')
    localStorage.removeItem('yoto_refresh_token')
    setAccessToken(null)
  }

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <h1>🎵 YotoPodcast</h1>
          {accessToken && (
            <button onClick={handleLogout} className="logout-btn">
              Logout
            </button>
          )}
        </header>

        <main className="app-main">
          <Routes>
            <Route 
              path="/login" 
              element={accessToken ? <Navigate to="/" /> : <Login onLogin={handleLogin} />} 
            />
            <Route 
              path="/" 
              element={
                accessToken ? (
                  <div className="dashboard">
                    <UploadForm accessToken={accessToken} />
                    <PlaylistManager accessToken={accessToken} />
                  </div>
                ) : (
                  <Navigate to="/login" />
                )
              } 
            />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App