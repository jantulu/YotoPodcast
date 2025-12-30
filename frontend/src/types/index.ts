export interface Playlist {
  cardId: string
  title: string
  createdAt?: string
  updatedAt?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token?: string
}

export interface UploadResponse {
  success: boolean
  message: string
  cardId?: string
  data?: any
}