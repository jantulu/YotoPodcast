import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../services/api'

interface AuthCallbackProps {
  onLogin: (token: string) => void
}

export default function AuthCallback({ onLogin }: AuthCallbackProps) {
  const [searchParams] = useSearchParams()
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const code = searchParams.get('code')
    
    if (!code) {
      setError('No authorization code received')
      return
    }

    const exchangeToken = async () => {
      try {
        const tokenData = await api.auth.exchangeToken(code)
        onLogin(tokenData.access_token)
        
        if (tokenData.refresh_token) {
          localStorage.setItem('yoto_refresh_token', tokenData.refresh_token)
        }
        
        navigate('/')
      } catch (err) {
        setError('Failed to authenticate. Please try again.')
        console.error('Auth error:', err)
      }
    }

    exchangeToken()
  }, [searchParams, onLogin, navigate])

  if (error) {
    return (
      <div className="auth-callback">
        <div className="error-message">{error}</div>
        <button onClick={() => navigate('/login')}>Back to Login</button>
      </div>
    )
  }

  return (
    <div className="auth-callback">
      <p>Authenticating...</p>
    </div>
  )
}