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
3. Register a new application
4. Copy your Client ID and Client Secret
5. Set the redirect URI to `http://localhost:3000/callback`

### Environment Variables

Edit `.env` file with your credentials:
```bash
YOTO_CLIENT_ID=your_client_id_here
YOTO_CLIENT_SECRET=your_client_secret_here
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

## Project Structure
YotoPodcast/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── services/
│   │   └── yoto_service.py  # Yoto API integration
│   ├── routes/
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── upload.py        # Upload endpoints
│   │   └── playlists.py     # Playlist management
│   └── models/
│       └── schemas.py       # Pydantic models
├── frontend/
│   └── src/
│       ├── components/      # React components
│       ├── services/        # API service layer
│       └── types/           # TypeScript types
└── docker-compose.yml

## Troubleshooting

### Upload fails with permission error
- Make sure you're logged in with a valid access token
- Check that your Yoto API credentials are correct
- Verify the audio file is a supported format (MP3, M4A, WAV)

### Playlist not updating
- The key fix: Make sure `cardId` is included in the request body when updating
- Check the backend logs for detailed error messages

### Authentication issues
- Verify your redirect URI matches exactly in Yoto developer settings
- Check that CLIENT_ID and CLIENT_SECRET are correct in `.env`

## Key Implementation Details

### The Fix: Updating Existing Playlists

The critical fix for updating existing playlists is including the `cardId` in the request body:
```python
def update_existing_playlist(self, card_id: str, title: str, chapters: List[Dict[str, Any]]):
    content = {
        "cardId": card_id,  # THIS IS CRITICAL!
        "title": title,
        "content": {
            "chapters": chapters,
            "config": {"resumeTimeout": 2592000},
            "playbackType": "linear"
        }
    }
    response = requests.post(f"{self.BASE_URL}/content", headers=self.headers, json=content)
    return response.json()
```

Without `cardId`, the API creates a new playlist instead of updating the existing one.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License - feel free to use this project however you'd like!

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework
- [Yoto API](https://yoto.dev/) - Audio content platform