// This component is no longer needed with device flow, but keeping for compatibility
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    // Redirect to home since we're using device flow now
    navigate('/')
  }, [navigate])

  return (
    <div className="auth-callback">
      <p>Redirecting...</p>
    </div>
  )
}