import { Playlist, TokenResponse, DeviceCodeResponse, UploadResponse } from '../types'

const API_BASE = '/api'

export const api = {
  auth: {
    initiateDeviceFlow: async (): Promise<DeviceCodeResponse> => {
      const response = await fetch(`${API_BASE}/auth/device/code`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to initiate device flow')
      return response.json()
    },

    pollDeviceToken: async (deviceCode: string): Promise<TokenResponse | null> => {
      const response = await fetch(
        `${API_BASE}/auth/device/token?device_code=${deviceCode}`,
        { method: 'POST' }
      )
      
      // 202 means still pending
      if (response.status === 202) {
        return null
      }
      
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Token poll failed')
      }
      
      return response.json()
    },

    refreshToken: async (refreshToken: string): Promise<TokenResponse> => {
      const response = await fetch(
        `${API_BASE}/auth/refresh?refresh_token=${refreshToken}`,
        { method: 'POST' }
      )
      if (!response.ok) throw new Error('Token refresh failed')
      return response.json()
    },
  },

  playlists: {
    getAll: async (accessToken: string): Promise<Playlist[]> => {
      const response = await fetch(
        `${API_BASE}/playlists?access_token=${accessToken}`
      )
      const data = await response.json()
      return data.playlists
    },

    getById: async (cardId: string, accessToken: string): Promise<any> => {
      const response = await fetch(
        `${API_BASE}/playlists/${cardId}?access_token=${accessToken}`
      )
      const data = await response.json()
      return data.playlist
    },

    delete: async (cardId: string, accessToken: string): Promise<void> => {
      const response = await fetch(
        `${API_BASE}/playlists/${cardId}?access_token=${accessToken}`,
        { method: 'DELETE' }
      )
      if (!response.ok) throw new Error('Delete failed')
    },
  },

  upload: async (
    audioFile: File,
    title: string,
    accessToken: string,
    playlistCardId?: string
  ): Promise<UploadResponse> => {
    const formData = new FormData()
    formData.append('audio', audioFile)
    formData.append('title', title)
    formData.append('access_token', accessToken)
    if (playlistCardId) {
      formData.append('playlist_card_id', playlistCardId)
    }

    const response = await fetch(`${API_BASE}/upload`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Upload failed')
    }

    return response.json()
  },
}