import { useState, useEffect } from 'react'
import { api } from '../services/api'
import { DeviceCodeResponse } from '../types'

interface LoginProps {
  onLogin: (token: string) => void
}

export default function Login({ onLogin }: LoginProps) {
  const [loading, setLoading] = useState(false)
  const [deviceCode, setDeviceCode] = useState<DeviceCodeResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!deviceCode) return

    const pollInterval = deviceCode.interval * 1000 // Convert to milliseconds
    let timeoutId: NodeJS.Timeout

    const pollForToken = async () => {
      try {
        const tokenData = await api.auth.pollDeviceToken(deviceCode.device_code)
        
        if (tokenData) {
          // Successfully got token
          onLogin(tokenData.access_token)
          if (tokenData.refresh_token) {
            localStorage.setItem('yoto_refresh_token', tokenData.refresh_token)
          }
          setDeviceCode(null)
        } else {
          // Still pending, poll again
          timeoutId = setTimeout(pollForToken, pollInterval)
        }
      } catch (err: any) {
        setError(err.message || 'Authorization failed')
        setDeviceCode(null)
        setLoading(false)
      }
    }

    // Start polling
    timeoutId = setTimeout(pollForToken, pollInterval)

    return () => {
      if (timeoutId) clearTimeout(timeoutId)
    }
  }, [deviceCode, onLogin])

  const handleLogin = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await api.auth.initiateDeviceFlow()
      setDeviceCode(response)
    } catch (err: any) {
      setError(err.message || 'Failed to initiate login')
      setLoading(false)
    }
  }

  if (deviceCode) {
    return (
      <div className="login-container">
        <h2>Authorize YotoPodcast</h2>
        
        <div className="device-code-box">
          <p className="instruction">Go to this URL on any device:</p>
          <a 
            href={deviceCode.verification_uri} 
            target="_blank" 
            rel="noopener noreferrer"
            className="verification-link"
          >
            {deviceCode.verification_uri}
          </a>
          
          <p className="instruction" style={{ marginTop: '20px' }}>
            Enter this code:
          </p>
          <div className="user-code">{deviceCode.user_code}</div>
          
          <p className="waiting-text">
            ⏳ Waiting for authorization...
          </p>
        </div>

        <button 
          onClick={() => {
            setDeviceCode(null)
            setLoading(false)
          }}
          className="cancel-btn"
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <div className="login-container">
      <h2>Welcome to YotoPodcast</h2>
      <p>Upload your podcasts to Yoto playlists</p>
      
      {error && (
        <div className="error-message">{error}</div>
      )}
      
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