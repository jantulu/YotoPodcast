# YotoPodcast

A web application for uploading podcast episodes to Yoto playlists.

## Features

- 🔐 OAuth authentication with Yoto
- 📤 Upload audio files to new or existing playlists
- 📋 View and manage your Yoto playlists
- 🎵 Automatic audio transcoding
- 🐳 Docker support for easy deployment

## Prerequisites

- Docker and Docker Compose
- Yoto Developer Account (get credentials at https://yoto.dev)

## Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/YotoPodcast.git
cd YotoPodcast
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env and add your Yoto credentials
```

3. **Start the application**
```bash
docker-compose up -d
```

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Configuration

### Getting Yoto API Credentials

1. Go to https://yoto.dev
2. Create a developer account
3. Register a new application (public, no secret)
4. Copy your Client ID
5. Set the redirect URI to `http://localhost:3000/callback`

### Environment Variables

Edit `.env` file with your credentials:
```bash
YOTO_CLIENT_ID=your_client_id_here
YOTO_REDIRECT_URI=http://localhost:3000/callback
```

## Usage

### Uploading Podcasts

1. **Login** with your Yoto account
2. **Choose upload mode**:
   - Create new playlist: Upload will create a new playlist
   - Add to existing: Select from your existing playlists
3. **Enter episode title** and **select audio file**
4. **Click Upload** - the app will:
   - Upload your audio file
   - Wait for Yoto to transcode it
   - Add it to the selected playlist

### Managing Playlists

- View all your playlists in the playlist manager
- Click "View" to see playlist details
- Click "Delete" to remove a playlist

## API Endpoints

### Authentication
- `GET /api/auth/authorize` - Get OAuth authorization URL
- `POST /api/auth/token` - Exchange authorization code for access token
- `POST /api/auth/refresh` - Refresh access token

### Playlists
- `GET /api/playlists` - Get all user playlists
- `GET /api/playlists/{cardId}` - Get specific playlist
- `DELETE /api/playlists/{cardId}` - Delete playlist

### Upload
- `POST /api/upload` - Upload podcast episode

## Development

### Running Locally (without Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
