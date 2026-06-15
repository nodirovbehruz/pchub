# PCHub Backend API Reference

## Table of Contents

1. [Authentication](#authentication)
2. [Computer Management](#computer-management)
3. [Game Library](#game-library)
4. [Game Sessions](#game-sessions)
5. [User Dashboard](#user-dashboard)
6. [Error Handling](#error-handling)

---

## Base URL

```
Production: https://your-domain.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

All endpoints (except login/register) require authentication via JWT Bearer token.

### Headers

```
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

---

## Authentication Endpoints

### Login

Authenticate user and receive JWT tokens.

**Endpoint**: `POST /accounts/login/`

**Request Body**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "player1",
    "email": "player@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

**Error Responses**:
- `401 Unauthorized`: Invalid credentials
- `400 Bad Request`: Missing required fields

---

### Token Refresh

Refresh expired access token using refresh token.

**Endpoint**: `POST /accounts/token/refresh/`

**Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## Computer Management

### Register Computer

Register or update a computer with the backend. If a computer with the same `hardware_id` exists, it will be updated instead of creating a new record.

**Endpoint**: `POST /computers/register/`

**Authentication**: Required

**Request Body**:
```json
{
  "name": "Gaming-PC-01",
  "hardware_id": "abc123def456...",
  "description": "Main gaming computer",
  "cpu_model": "Intel Core i7-12700K",
  "cpu_cores": 12,
  "cpu_threads": 20,
  "ram_total_gb": 32.0,
  "gpu_model": "NVIDIA RTX 3080",
  "storage_total_gb": 1000.0,
  "os_name": "Windows",
  "os_version": "11 Pro",
  "ip_address": "192.168.1.100",
  "mac_address": "00:11:22:33:44:55"
}
```

**Required Fields**:
- `name` (string)
- `hardware_id` (string, max 64 chars)

**Optional Fields**:
- All other fields are optional but recommended for better tracking

**Response** (201 Created):
```json
{
  "id": 5,
  "name": "Gaming-PC-01",
  "slug": "gaming-pc-01",
  "description": "Main gaming computer",
  "hardware_id": "abc123def456...",
  "owner_username": "admin",
  "cpu_model": "Intel Core i7-12700K",
  "cpu_cores": 12,
  "cpu_threads": 20,
  "ram_total_gb": "32.00",
  "gpu_model": "NVIDIA RTX 3080",
  "storage_total_gb": "1000.00",
  "os_name": "Windows",
  "os_version": "11 Pro",
  "ip_address": "192.168.1.100",
  "mac_address": "00:11:22:33:44:55",
  "status": "ONLINE",
  "is_active": true,
  "last_seen": "2025-12-20T10:30:00Z",
  "installed_games_count": 0,
  "total_gaming_hours": "0.00",
  "created_at": "2025-12-20T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Missing required fields or validation error
- `401 Unauthorized`: Invalid or missing authentication token

---

### Send Heartbeat

Send heartbeat to keep computer status as ONLINE. Should be called every 30 seconds.

**Endpoint**: `POST /computers/{computer_id}/heartbeat/`

**Authentication**: Required

**URL Parameters**:
- `computer_id` (integer): ID of the computer

**Request Body**: Empty `{}`

**Response** (200 OK):
```json
{
  "success": true,
  "timestamp": "2025-12-20T10:35:00Z",
  "status": "ONLINE"
}
```

**Error Responses**:
- `404 Not Found`: Computer not found
- `401 Unauthorized`: Invalid or missing authentication token

---

### Get Computer Details

Get detailed information about a specific computer.

**Endpoint**: `GET /computers/{computer_id}/`

**Authentication**: Required

**URL Parameters**:
- `computer_id` (integer): ID of the computer

**Response** (200 OK):
```json
{
  "computer": {
    "id": 5,
    "name": "Gaming-PC-01",
    "slug": "gaming-pc-01",
    "hardware_id": "abc123def456...",
    "status": "ONLINE",
    "cpu_model": "Intel Core i7-12700K",
    "ram_total_gb": "32.00",
    "gpu_model": "NVIDIA RTX 3080"
  },
  "installed_games_count": 15,
  "total_gaming_hours": 235.5,
  "total_games_size_gb": 450.2,
  "latest_metrics": {
    "cpu_usage_percent": 45.2,
    "ram_usage_percent": 65.8,
    "timestamp": "2025-12-20T10:30:00Z"
  },
  "status": "ONLINE",
  "last_seen": "2025-12-20T10:35:00Z",
  "installed_games": [
    {
      "id": 1,
      "game": {
        "id": 10,
        "steam_app_id": 730,
        "name": "Counter-Strike 2",
        "icon_url": "https://..."
      },
      "is_installed": true,
      "install_size_gb": "25.50",
      "last_played": "2025-12-19T15:20:00Z"
    }
  ]
}
```

---

### List All Computers

Get list of all registered computers.

**Endpoint**: `GET /computers/`

**Authentication**: Required

**Query Parameters**:
- `my_computers` (boolean, optional): Filter to show only current user's computers
  - Example: `/computers/?my_computers=true`

**Response** (200 OK):
```json
[
  {
    "id": 5,
    "name": "Gaming-PC-01",
    "hardware_id": "abc123...",
    "status": "ONLINE",
    "installed_games_count": 15,
    "total_gaming_hours": "235.50",
    "last_seen": "2025-12-20T10:35:00Z"
  },
  {
    "id": 6,
    "name": "Gaming-PC-02",
    "hardware_id": "def456...",
    "status": "OFFLINE",
    "installed_games_count": 12,
    "total_gaming_hours": "180.25",
    "last_seen": "2025-12-19T22:15:00Z"
  }
]
```

---

## Game Library

### List All Games

Get list of all available games in the system.

**Endpoint**: `GET /games/games/`

**Authentication**: Required

**Query Parameters**:
- `search` (string, optional): Search by game name
- `is_active` (boolean, optional): Filter active/inactive games

**Response** (200 OK):
```json
[
  {
    "id": 10,
    "steam_app_id": 730,
    "name": "Counter-Strike 2",
    "slug": "counter-strike-2",
    "icon_url": "https://cdn.akamai.steamstatic.com/...",
    "developer": "Valve",
    "publisher": "Valve",
    "release_date": "2023-09-27",
    "total_players": 1250,
    "total_hours_played": 15420.5
  }
]
```

---

### Get Game Details

Get detailed information about a specific game.

**Endpoint**: `GET /games/games/{slug}/`

**Authentication**: Required

**URL Parameters**:
- `slug` (string): Game slug (URL-friendly name)

**Response** (200 OK):
```json
{
  "id": 10,
  "steam_app_id": 730,
  "name": "Counter-Strike 2",
  "slug": "counter-strike-2",
  "description": "For over two decades, Counter-Strike has offered...",
  "icon_url": "https://...",
  "header_image_url": "https://...",
  "developer": "Valve",
  "publisher": "Valve",
  "release_date": "2023-09-27",
  "is_active": true,
  "total_players": 1250,
  "total_hours_played": 15420.5,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-12-20T10:00:00Z"
}
```

---

### Get Computer Games

Get list of games installed on a specific computer.

**Endpoint**: `GET /games/computer/games/`

**Authentication**: Required

**Query Parameters**:
- `computer_id` (integer, optional): ID of the computer
- `hardware_id` (string, optional): Hardware ID of the computer

**Note**: Provide either `computer_id` OR `hardware_id` (not both)

**Example**: `/games/computer/games/?hardware_id=abc123def456...`

**Response** (200 OK):
```json
{
  "computer": {
    "id": 5,
    "name": "Gaming-PC-01",
    "hardware_id": "abc123def456..."
  },
  "games": [
    {
      "id": 10,
      "steam_app_id": 730,
      "name": "Counter-Strike 2",
      "slug": "counter-strike-2",
      "icon_url": "https://...",
      "header_image_url": "https://...",
      "developer": "Valve",
      "publisher": "Valve"
    },
    {
      "id": 11,
      "steam_app_id": 570,
      "name": "Dota 2",
      "slug": "dota-2",
      "icon_url": "https://...",
      "header_image_url": "https://...",
      "developer": "Valve",
      "publisher": "Valve"
    }
  ],
  "total_games": 2
}
```

**Error Responses**:
- `400 Bad Request`: Missing `computer_id` or `hardware_id`
- `404 Not Found`: Computer not found

---

## Game Sessions

### Start Game Session

Start a new game session when user launches a game.

**Endpoint**: `POST /games/sessions/start/`

**Authentication**: Required

**Request Body**:
```json
{
  "steam_app_id": 730,
  "computer_id": 5,
  "game_name": "Counter-Strike 2"
}
```

**Required Fields**:
- `steam_app_id` (integer): Steam App ID of the game
- `computer_id` (integer): ID of the computer

**Optional Fields**:
- `game_name` (string): Game name for auto-creation if game doesn't exist

**Response** (200 OK):
```json
{
  "id": 1,
  "account_username": "player1",
  "game": {
    "id": 10,
    "steam_app_id": 730,
    "name": "Counter-Strike 2",
    "slug": "counter-strike-2",
    "icon_url": "https://..."
  },
  "computer_name": "Gaming-PC-01",
  "total_hours_played": "45.50",
  "current_session_start": "2025-12-20T10:30:00Z",
  "session_status": "ACTIVE",
  "last_played": "2025-12-20T10:30:00Z",
  "created_at": "2025-01-15T08:00:00Z"
}
```

---

### Update Game Session

Add hours to an active game session. Call this periodically (e.g., every 5-10 minutes).

**Endpoint**: `POST /games/sessions/update/`

**Authentication**: Required

**Request Body**:
```json
{
  "steam_app_id": 730,
  "computer_id": 5,
  "hours_to_add": 0.1
}
```

**Required Fields**:
- `steam_app_id` (integer): Steam App ID of the game
- `computer_id` (integer): ID of the computer
- `hours_to_add` (float): Hours to add (e.g., 0.1 = 6 minutes, 0.5 = 30 minutes)

**Optional Fields**:
- `game_name` (string): Game name for auto-creation if game doesn't exist

**Response** (200 OK):
```json
{
  "id": 1,
  "account_username": "player1",
  "game": {
    "id": 10,
    "steam_app_id": 730,
    "name": "Counter-Strike 2",
    "icon_url": "https://..."
  },
  "computer_name": "Gaming-PC-01",
  "total_hours_played": "45.60",
  "current_session_start": "2025-12-20T10:30:00Z",
  "session_status": "ACTIVE",
  "last_played": "2025-12-20T10:40:00Z"
}
```

**Notes**:
- The `hours_to_add` will be added to the `total_hours_played`
- If the session doesn't exist, it will be created automatically
- If the game doesn't exist in the database, it will be created if `game_name` is provided

---

### End Game Session

End an active game session when the game closes.

**Endpoint**: `POST /games/sessions/end/`

**Authentication**: Required

**Request Body**:
```json
{
  "steam_app_id": 730,
  "computer_id": 5,
  "hours_played": 2.5
}
```

**Required Fields**:
- `steam_app_id` (integer): Steam App ID of the game
- `computer_id` (integer): ID of the computer

**Optional Fields**:
- `hours_played` (float): Total hours played in this session (will be added to total)

**Response** (200 OK):
```json
{
  "id": 1,
  "account_username": "player1",
  "game": {
    "id": 10,
    "steam_app_id": 730,
    "name": "Counter-Strike 2",
    "icon_url": "https://..."
  },
  "computer_name": "Gaming-PC-01",
  "total_hours_played": "48.00",
  "current_session_start": null,
  "session_status": "ENDED",
  "last_played": "2025-12-20T13:00:00Z"
}
```

---

### List User Sessions

Get all game sessions for the authenticated user.

**Endpoint**: `GET /games/sessions/`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "sessions": [
    {
      "id": 1,
      "game": {
        "id": 10,
        "steam_app_id": 730,
        "name": "Counter-Strike 2",
        "icon_url": "https://..."
      },
      "computer_name": "Gaming-PC-01",
      "total_hours_played": "48.00",
      "current_session_start": null,
      "session_status": "ENDED",
      "last_played": "2025-12-20T13:00:00Z"
    }
  ],
  "statistics": {
    "total_hours_played": 125.5,
    "total_games": 15,
    "total_sessions": 243
  }
}
```

---

## User Dashboard

### Get User Dashboard

Get comprehensive gaming statistics and data for the authenticated user.

**Endpoint**: `GET /games/dashboard/`

**Authentication**: Required

**Response** (200 OK):
```json
{
  "user": {
    "username": "player1",
    "email": "player@example.com",
    "id": 1
  },
  "statistics": {
    "total_hours_played": 125.5,
    "total_games": 15,
    "total_sessions": 243
  },
  "most_played_games": [
    {
      "id": 1,
      "account_username": "player1",
      "game": {
        "id": 10,
        "steam_app_id": 730,
        "name": "Counter-Strike 2",
        "slug": "counter-strike-2",
        "icon_url": "https://..."
      },
      "computer_name": "Gaming-PC-01",
      "total_hours_played": "48.00",
      "session_status": "ENDED",
      "last_played": "2025-12-20T13:00:00Z",
      "created_at": "2025-01-15T08:00:00Z"
    }
  ],
  "recent_sessions": [
    {
      "id": 5,
      "game": {
        "id": 15,
        "steam_app_id": 570,
        "name": "Dota 2",
        "icon_url": "https://..."
      },
      "total_hours_played": "12.50",
      "last_played": "2025-12-19T20:30:00Z"
    }
  ],
  "active_session": null
}
```

**Response Fields**:
- `user`: Current user information
- `statistics`: Overall gaming statistics
  - `total_hours_played`: Total hours across all games
  - `total_games`: Number of unique games played
  - `total_sessions`: Number of gaming sessions
- `most_played_games`: Top 5 most played games (ordered by hours)
- `recent_sessions`: Last 10 gaming sessions (ordered by date)
- `active_session`: Currently active session (or `null` if none)

---

## Error Handling

### Standard Error Response Format

```json
{
  "error": "Error message description",
  "detail": "Detailed error information"
}
```

### HTTP Status Codes

| Status Code | Meaning |
|------------|---------|
| 200 OK | Request successful |
| 201 Created | Resource created successfully |
| 400 Bad Request | Invalid request data or missing required fields |
| 401 Unauthorized | Missing or invalid authentication token |
| 403 Forbidden | User doesn't have permission to access resource |
| 404 Not Found | Resource not found |
| 500 Internal Server Error | Server error |

---

## Rate Limiting

Currently, there are no rate limits enforced. However, it is recommended to:

- Send heartbeats every **30 seconds** (not more frequently)
- Update sessions every **5-10 minutes** (not every second)
- Avoid excessive API calls in loops

---

## Best Practices

### Session Tracking

1. **Start session** when game launches
2. **Update session** every 5-10 minutes with hours played
3. **End session** when game closes
4. Always include `computer_id` for proper tracking

### Heartbeat

- Send heartbeat every **30 seconds**
- Don't send more frequently to avoid server load
- Handle heartbeat failures gracefully (retry after 30 seconds)

### Error Handling

- Always check HTTP status codes
- Handle `401 Unauthorized` by re-authenticating
- Implement retry logic for network failures
- Log errors for debugging

### Authentication

- Store JWT tokens securely in memory
- Refresh tokens before they expire
- Never log or display tokens in plain text

---

## Example API Call Sequence

### Typical C# App Startup

1. **Generate/Load Hardware ID**
2. **Login**: `POST /accounts/login/`
3. **Register PC**: `POST /computers/register/`
4. **Start Heartbeat**: `POST /computers/{id}/heartbeat/` (every 30s)
5. **Load Dashboard**: `GET /games/dashboard/`
6. **Get Computer Games**: `GET /games/computer/games/?hardware_id=...`

### Typical Game Session

1. **User selects game**
2. **Start Session**: `POST /games/sessions/start/`
3. **Launch game**
4. **Update Session**: `POST /games/sessions/update/` (every 5-10 minutes)
5. **Game closes**
6. **End Session**: `POST /games/sessions/end/`

---

## Support

For questions or issues with the API, please contact your system administrator or refer to:

- [C# Integration Guide](./CSharp-Integration-Guide.md)
- [Architecture Documentation](./Architecture.md)
