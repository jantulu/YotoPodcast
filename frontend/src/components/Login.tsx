import { useState } from 'react'
import { api } from '../services/api'

export default function Login() {
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    setLoading(true)
    try {
      const { authorization_url } = await api.auth.getAuthorizeUrl()
      window.location.href = authorization_url
    } catch (error) {
      console.error('Login failed:', error)
      alert('Failed to initiate login')
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <h2>Welcome to YotoPodcast</h2>
      <p>Upload your podcasts to Yoto playlists</p>
      <button 
        onClick={handleLogin} 
        disabled={loading}
        className="login-btn"
      >
        {loading ? 'Connecting...' : 'Login with Yoto'}
      </button>
    </div>
  )
}