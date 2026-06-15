# PCHub Documentation

Welcome to the PCHub documentation. This system is designed for managing gaming clubs and internet cafés, providing comprehensive PC tracking, game library management, and user session monitoring.

## Documentation Overview

This documentation package contains everything you need to understand and integrate with the PCHub backend system.

### Available Documents

| Document | Description | Target Audience |
|----------|-------------|----------------|
| **[CSharp-Integration-Guide.md](./CSharp-Integration-Guide.md)** | Complete guide for building and integrating the C# desktop application with the backend API | C# Developers |
| **[API-Reference.md](./API-Reference.md)** | Detailed API endpoint reference with request/response examples | All Developers |
| **[Architecture.md](./Architecture.md)** | System architecture, database schema, data flows, and deployment guide | System Architects, DevOps |

---

## Quick Start

### For C# Developers

If you're building the desktop application for gaming PCs:

1. Start with **[CSharp-Integration-Guide.md](./CSharp-Integration-Guide.md)**
2. Implement the hardware ID generation logic
3. Integrate user authentication
4. Add session tracking functionality
5. Refer to **[API-Reference.md](./API-Reference.md)** for endpoint details

### For Backend Developers

If you're working on the Django backend:

1. Review **[Architecture.md](./Architecture.md)** for system overview
2. Understand the database schema and relationships
3. Use **[API-Reference.md](./API-Reference.md)** to understand existing endpoints
4. Follow Django best practices for adding new features

### For System Administrators

If you're deploying or managing the system:

1. Read **[Architecture.md](./Architecture.md)** for deployment architecture
2. Review security considerations
3. Set up monitoring and logging as recommended
4. Understand the scalability options

---

## System Components

### C# Desktop Application

**Purpose**: Installed on each gaming PC in the café

**Key Features**:
- Unique hardware ID generation for PC identification
- User authentication and dashboard
- Game selection and launching
- Session time tracking
- Heartbeat system for PC status monitoring
- Admin-level control to prevent unauthorized closure

**Documentation**: [CSharp-Integration-Guide.md](./CSharp-Integration-Guide.md)

---

### Django Backend API

**Purpose**: Central server managing all gaming club data

**Key Features**:
- User authentication and management (JWT)
- Computer registration and tracking
- Game library with Steam integration
- Session tracking and statistics
- User dashboard with gaming analytics
- Admin panel for system management

**Documentation**:
- [API-Reference.md](./API-Reference.md)
- [Architecture.md](./Architecture.md)

---

## Core Concepts

### Hardware ID

Each PC generates a **unique hardware identifier** based on:
- CPU ID
- Motherboard serial number
- Primary MAC address

This ID is persistent and used to track the PC across sessions, even if the computer name or IP address changes.

**Important**: The hardware ID should NEVER be regenerated after initial creation.

---

### Session Tracking

Gaming sessions are tracked in three stages:

1. **Start**: When a user launches a game
2. **Update**: Periodically (every 5-10 minutes) while the game is running
3. **End**: When the game closes

Each session records:
- Which user played
- Which game was played
- Which computer was used
- Total hours played

---

### Heartbeat System

The C# application sends a heartbeat to the backend every **30 seconds** to indicate that the PC is still online and operational.

If a PC stops sending heartbeats, its status automatically changes to `OFFLINE` after a timeout period.

---

## API Workflow

### Typical Application Startup

```
1. Generate/Load Hardware ID
   └─► Check pc_config.json
       ├─► Exists: Load hardware_id
       └─► New: Generate new hardware_id

2. User Login
   └─► POST /api/v1/accounts/login/
       └─► Receive JWT token

3. PC Registration
   └─► POST /api/v1/computers/register/
       └─► Backend registers or updates PC

4. Start Heartbeat Timer
   └─► POST /api/v1/computers/{id}/heartbeat/ (every 30s)

5. Load User Dashboard
   └─► GET /api/v1/games/dashboard/
       └─► Display user statistics and games

6. Get Available Games
   └─► GET /api/v1/games/computer/games/?hardware_id=...
       └─► Show game selection menu
```

### Typical Gaming Session

```
1. User Selects Game
   └─► Display game information

2. Start Session
   └─► POST /api/v1/games/sessions/start/
       └─► Backend creates session record

3. Launch Game
   └─► Start game process

4. Track Session
   └─► POST /api/v1/games/sessions/update/ (every 5-10 min)
       └─► Backend updates total hours

5. Game Closes
   └─► POST /api/v1/games/sessions/end/
       └─► Backend finalizes session
```

---

## Key Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/accounts/login/` | User login |
| POST | `/api/v1/accounts/token/refresh/` | Refresh JWT token |

### Computer Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/computers/register/` | Register/update PC |
| POST | `/api/v1/computers/{id}/heartbeat/` | Send heartbeat |
| GET | `/api/v1/computers/` | List all computers |
| GET | `/api/v1/computers/{id}/` | Get computer details |

### Games

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/games/games/` | List all games |
| GET | `/api/v1/games/games/{slug}/` | Get game details |
| GET | `/api/v1/games/computer/games/` | Get games on a PC |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/games/sessions/start/` | Start game session |
| POST | `/api/v1/games/sessions/update/` | Update session hours |
| POST | `/api/v1/games/sessions/end/` | End game session |
| GET | `/api/v1/games/sessions/` | List user sessions |

### Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/games/dashboard/` | User gaming dashboard |

For complete endpoint details, see **[API-Reference.md](./API-Reference.md)**.

---

## Database Models

### Core Models

1. **Account** (Django User)
   - Standard Django user model
   - Stores user credentials and profile

2. **Computer**
   - Represents a gaming PC
   - Has unique `hardware_id`
   - Tracks specs, status, and location

3. **Game**
   - Represents a game title
   - Linked to Steam via `steam_app_id`
   - Stores metadata (name, developer, images)

4. **ComputerGame**
   - Many-to-many relationship
   - Tracks which games are installed on which PCs

5. **GameSession**
   - Tracks user gaming sessions
   - Records hours played per user per game per computer
   - Unique constraint: (account, game, computer)

For detailed schema, see **[Architecture.md](./Architecture.md)**.

---

## Security Considerations

### C# Application

- **Admin Privileges**: Must run as administrator
- **Kiosk Mode**: Prevents users from closing the app
- **Secure Storage**: JWT tokens stored in memory only
- **Hardware ID**: Generated once and never changes

### Backend API

- **HTTPS Only**: All production traffic must use HTTPS
- **JWT Authentication**: Stateless, secure token-based auth
- **Input Validation**: All inputs validated on the server
- **CORS**: Configured for trusted origins only

### Data Protection

- **Passwords**: Hashed using Django's PBKDF2 algorithm
- **Tokens**: Short-lived access tokens, long-lived refresh tokens
- **Audit Logging**: Track all admin actions

---

## Common Implementation Tasks

### Task 1: Generate Hardware ID

**Goal**: Create a unique, persistent identifier for each PC

**Steps**:
1. Read `pc_config.json` to check if hardware_id exists
2. If not, generate new ID using CPU + Motherboard + MAC
3. Hash the combined string using SHA256
4. Save to `pc_config.json`

**Reference**: [CSharp-Integration-Guide.md#hardware-id-generation](./CSharp-Integration-Guide.md#hardware-id-generation)

---

### Task 2: Authenticate User

**Goal**: Log in a user and obtain JWT token

**Steps**:
1. Collect username and password from user
2. POST to `/api/v1/accounts/login/`
3. Store `access` token for API calls
4. Store `refresh` token for token renewal

**Reference**: [API-Reference.md#login](./API-Reference.md#login)

---

### Task 3: Register PC

**Goal**: Register the PC with the backend

**Steps**:
1. Collect system information (CPU, RAM, GPU, etc.)
2. Get hardware_id from config file
3. POST to `/api/v1/computers/register/`
4. Save returned `computer_id` to config file

**Reference**: [CSharp-Integration-Guide.md#pc-registration](./CSharp-Integration-Guide.md#pc-registration)

---

### Task 4: Track Game Session

**Goal**: Record a user's gaming session

**Steps**:
1. When game launches: POST to `/api/v1/games/sessions/start/`
2. Every 5-10 minutes: POST to `/api/v1/games/sessions/update/`
3. When game closes: POST to `/api/v1/games/sessions/end/`

**Reference**: [CSharp-Integration-Guide.md#session-tracking](./CSharp-Integration-Guide.md#session-tracking)

---

## Troubleshooting

### Common Issues

#### PC Not Registering

**Symptoms**: POST to `/computers/register/` fails

**Solutions**:
- Verify `hardware_id` is being generated correctly
- Ensure user is authenticated (valid JWT token)
- Check network connectivity to backend
- Verify `hardware_id` and `name` are provided in request

---

#### Sessions Not Tracking

**Symptoms**: Gaming hours not updating in database

**Solutions**:
- Confirm `computer_id` is saved after registration
- Verify authentication token is valid
- Check that `steam_app_id` and `computer_id` match
- Ensure session start was called before update

---

#### Heartbeat Not Working

**Symptoms**: PC status shows OFFLINE despite being online

**Solutions**:
- Verify heartbeat timer is running (every 30s)
- Check that `computer_id` is correct
- Ensure authentication token hasn't expired
- Verify API endpoint URL is correct

---

#### Authentication Token Expired

**Symptoms**: API calls return 401 Unauthorized

**Solutions**:
- Use refresh token to get new access token
- POST to `/api/v1/accounts/token/refresh/`
- Update stored access token
- Re-authenticate if refresh token also expired

---

## Development Setup

### Backend Setup

```bash
# Clone repository
git clone <repository-url>
cd PCHubBackend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Testing API Endpoints

Use tools like:
- **Postman**: GUI tool for API testing
- **curl**: Command-line tool for API requests
- **Django REST Framework Browsable API**: Built-in web interface

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Set `DEBUG = False` in settings
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `SECRET_KEY`
- [ ] Configure PostgreSQL database
- [ ] Set up static files serving
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up monitoring and logging
- [ ] Configure CORS for allowed origins
- [ ] Set up database backups
- [ ] Configure JWT token expiration times

### Recommended Stack

- **Web Server**: Gunicorn + Nginx
- **Database**: PostgreSQL 13+
- **Caching**: Redis (optional)
- **Hosting**: AWS, DigitalOcean, Heroku
- **SSL**: Let's Encrypt

For detailed deployment guide, see **[Architecture.md#deployment-architecture](./Architecture.md#deployment-architecture)**.

---

## Support and Contributing

### Getting Help

- Review this documentation thoroughly
- Check **[API-Reference.md](./API-Reference.md)** for endpoint details
- Consult **[Architecture.md](./Architecture.md)** for system design questions

### Reporting Issues

When reporting issues, include:
- Detailed description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Error messages and logs
- System environment (OS, versions, etc.)

---

## Version History

### v1.0.0 (2025-12-20)

Initial release with:
- Computer registration with hardware ID
- User authentication (JWT)
- Game library management
- Session tracking
- User dashboard
- Heartbeat system
- Complete C# integration documentation

---

## License

[Add your license information here]

---

## Additional Resources

- **Django Documentation**: https://docs.djangoproject.com/
- **Django REST Framework**: https://www.django-rest-framework.org/
- **.NET Documentation**: https://learn.microsoft.com/dotnet/
- **Steam Web API**: https://steamcommunity.com/dev

---

## Summary

This documentation provides everything needed to:

1. **Understand** the PCHub system architecture
2. **Implement** a C# desktop application
3. **Integrate** with the backend API
4. **Deploy** the system to production
5. **Maintain** and scale the system

Start with the document that matches your role:
- **C# Developer**: [CSharp-Integration-Guide.md](./CSharp-Integration-Guide.md)
- **API Integration**: [API-Reference.md](./API-Reference.md)
- **System Design**: [Architecture.md](./Architecture.md)

Happy coding!
