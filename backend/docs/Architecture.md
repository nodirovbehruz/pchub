# PCHub System Architecture

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Details](#component-details)
4. [Database Schema](#database-schema)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [Deployment Architecture](#deployment-architecture)

---

## System Overview

PCHub is a comprehensive gaming club/internet café management system consisting of:

- **Backend API** (Django REST Framework): Manages computers, games, sessions, and user data
- **C# Desktop Application**: Installed on each gaming PC, handles user authentication, game launching, and session tracking
- **Admin Panel**: Django admin interface for managing the system

### Key Features

1. **PC Management**: Track and monitor gaming PCs with unique hardware IDs
2. **Game Library**: Manage available games with Steam integration
3. **Session Tracking**: Record gaming sessions with precise time tracking
4. **User Dashboard**: Show personalized gaming statistics
5. **Real-time Monitoring**: Track PC status with heartbeat system

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GAMING CLUB SETUP                           │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │  PC #1       │  │  PC #2       │  │  PC #N       │            │
│  │              │  │              │  │              │            │
│  │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │            │
│  │  │ C# App │  │  │  │ C# App │  │  │  │ C# App │  │            │
│  │  │        │  │  │  │        │  │  │  │        │  │            │
│  │  │ - Login│  │  │  │ - Login│  │  │  │ - Login│  │            │
│  │  │ - Games│  │  │  │ - Games│  │  │  │ - Games│  │            │
│  │  │ - Track│  │  │  │ - Track│  │  │  │ - Track│  │            │
│  │  └────┬───┘  │  │  └────┬───┘  │  │  └────┬───┘  │            │
│  └───────┼──────┘  └───────┼──────┘  └───────┼──────┘            │
│          │                 │                 │                    │
│          └─────────────────┼─────────────────┘                    │
│                            │                                       │
└────────────────────────────┼───────────────────────────────────────┘
                             │
                             │ HTTPS/REST API
                             │
┌────────────────────────────▼───────────────────────────────────────┐
│                      BACKEND SERVER                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │             Django REST Framework API                         │  │
│  │                                                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │ Computers   │  │   Games     │  │  Sessions   │          │  │
│  │  │ Management  │  │  Library    │  │  Tracking   │          │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │  │
│  │         │                │                │                  │  │
│  │         └────────────────┼────────────────┘                  │  │
│  │                          │                                   │  │
│  │  ┌─────────────────────────────────────────────────────────┐│  │
│  │  │          Repository Layer (Data Access)                  ││  │
│  │  └──────────────────────┬──────────────────────────────────┘│  │
│  └─────────────────────────┼───────────────────────────────────┘  │
│                            │                                       │
│  ┌─────────────────────────▼───────────────────────────────────┐  │
│  │                  PostgreSQL Database                         │  │
│  │                                                               │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │  │
│  │  │ Users    │  │Computers │  │  Games   │  │ Sessions │    │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │  │
│  │                                                               │  │
│  │  ┌──────────┐  ┌──────────┐                                 │  │
│  │  │Computer  │  │Computer  │                                 │  │
│  │  │  Games   │  │ Metrics  │                                 │  │
│  │  └──────────┘  └──────────┘                                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### C# Desktop Application

**Responsibilities**:
- Generate unique hardware ID for PC identification
- Authenticate users with backend
- Register/update PC information
- Display user dashboard with gaming statistics
- Show available games on the PC
- Launch games and track session time
- Send periodic heartbeats to maintain PC online status
- Prevent unauthorized app closure (admin-level lock)

**Technology**:
- .NET Framework 4.8+ or .NET 6.0+
- WPF or WinForms for UI
- HttpClient for API communication
- System.Management for hardware info

**Key Files**:
- `pc_config.json`: Stores hardware_id and computer_id

---

### Backend API (Django)

**Responsibilities**:
- User authentication and authorization (JWT)
- Computer registration and management
- Game library management
- Session tracking and statistics
- Real-time PC status monitoring
- Admin panel for system management

**Technology Stack**:
- Django 4.x
- Django REST Framework
- PostgreSQL database
- JWT authentication
- Celery (optional, for background tasks)

**App Structure**:
```
apps/
├── accounts/          # User authentication and management
├── computers/         # Computer/PC management
│   ├── models/        # Computer, ComputerGame, ComputerMetrics
│   ├── repositories/  # Data access layer
│   ├── services/      # Business logic
│   └── api/           # REST API endpoints
└── games/             # Game and session management
    ├── models/        # Game, GameSession
    ├── repositories/  # Data access layer
    ├── services/      # Business logic
    └── api/           # REST API endpoints
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐
│     Account     │
│  (Django User)  │
└────────┬────────┘
         │
         │ owner (1:N)
         │
         ▼
┌─────────────────────────────┐
│        Computer             │
├─────────────────────────────┤
│ id (PK)                     │
│ name                        │
│ hardware_id (UNIQUE)        │◄────┐
│ slug                        │     │
│ owner_id (FK → Account)     │     │
│ cpu_model, cpu_cores        │     │
│ ram_total_gb, gpu_model     │     │
│ os_name, os_version         │     │
│ ip_address, mac_address     │     │
│ status (ONLINE/OFFLINE)     │     │
│ last_seen                   │     │
└────────┬────────────────────┘     │
         │                          │
         │                          │
         │                          │
         ├─────────────────────────────┐
         │                             │
         │ computer (N:1)              │
         ▼                             │
┌──────────────────────┐               │
│   ComputerMetrics    │               │
├──────────────────────┤               │
│ id (PK)              │               │
│ computer_id (FK)     │               │
│ cpu_usage_percent    │               │
│ ram_usage_percent    │               │
│ timestamp            │               │
└──────────────────────┘               │
                                       │
         ┌─────────────────────────────┘
         │
         │ computer (N:1)
         ▼
┌───────────────────────────┐
│     ComputerGame          │
├───────────────────────────┤
│ id (PK)                   │
│ computer_id (FK)          │──┐
│ game_id (FK)              │  │
│ is_installed              │  │
│ install_path              │  │
│ install_size_gb           │  │
│ last_played               │  │
└───────────────────────────┘  │
                               │
                               │
         ┌─────────────────────┘
         │
         │ game (N:1)
         ▼
┌───────────────────────────┐
│          Game             │
├───────────────────────────┤
│ id (PK)                   │◄────┐
│ steam_app_id (UNIQUE)     │     │
│ name                      │     │
│ slug                      │     │
│ description               │     │
│ icon_url                  │     │
│ header_image_url          │     │
│ developer, publisher      │     │
│ release_date              │     │
└───────────────────────────┘     │
                                  │
         ┌────────────────────────┘
         │
         │ game (N:1)
         ▼
┌─────────────────────────────────┐
│        GameSession              │
├─────────────────────────────────┤
│ id (PK)                         │
│ account_id (FK → Account)       │
│ game_id (FK → Game)             │
│ computer_id (FK → Computer)     │
│ total_hours_played              │
│ current_session_start           │
│ session_status (ACTIVE/ENDED)   │
│ last_played                     │
│ UNIQUE(account, game, computer) │
└─────────────────────────────────┘
```

### Key Relationships

1. **Account → Computer**: One-to-Many (owner)
2. **Computer → ComputerGame**: One-to-Many
3. **Game → ComputerGame**: One-to-Many
4. **Account + Game + Computer → GameSession**: Unique together

### Important Constraints

- `Computer.hardware_id`: **UNIQUE** - ensures PC uniqueness
- `Game.steam_app_id`: **UNIQUE** - prevents duplicate games
- `GameSession (account, game, computer)`: **UNIQUE TOGETHER** - one session record per user per game per computer

---

## Data Flow

### 1. PC Registration Flow

```
C# App Startup
    │
    ├─► Generate/Load Hardware ID
    │   (from pc_config.json or generate new)
    │
    ├─► Authenticate User
    │   POST /api/v1/accounts/login/
    │   └─► Receive JWT token
    │
    ├─► Register PC
    │   POST /api/v1/computers/register/
    │   {
    │     hardware_id: "abc123...",
    │     name: "PC-01",
    │     cpu_model: "...",
    │     ...
    │   }
    │   │
    │   └─► Backend checks if hardware_id exists
    │       ├─► Exists: Update existing computer
    │       └─► New: Create new computer
    │
    └─► Save computer_id to pc_config.json
```

### 2. User Login and Dashboard Flow

```
User Logs In
    │
    ├─► POST /api/v1/accounts/login/
    │   └─► Receive JWT token
    │
    ├─► GET /api/v1/games/dashboard/
    │   └─► Receive:
    │       ├─ User info
    │       ├─ Total statistics
    │       ├─ Most played games (top 5)
    │       ├─ Recent sessions
    │       └─ Active session (if any)
    │
    └─► Display Dashboard UI
```

### 3. Game Selection Flow

```
User Wants to Play
    │
    ├─► GET /api/v1/games/computer/games/?hardware_id=...
    │   └─► Receive list of installed games on this PC
    │
    ├─► Display Game Selection UI
    │
    └─► User selects a game
```

### 4. Game Session Flow

```
User Launches Game
    │
    ├─► POST /api/v1/games/sessions/start/
    │   {
    │     steam_app_id: 730,
    │     computer_id: 5
    │   }
    │   └─► Backend creates/updates GameSession
    │       └─► Sets session_status = ACTIVE
    │           Sets current_session_start = now()
    │
    ├─► Launch Game Process
    │
    ├─► Start Session Update Timer (every 5-10 min)
    │   │
    │   └─► POST /api/v1/games/sessions/update/
    │       {
    │         steam_app_id: 730,
    │         computer_id: 5,
    │         hours_to_add: 0.1
    │       }
    │       └─► Backend adds hours to total_hours_played
    │
    ├─► Monitor Game Process
    │
    └─► Game Closes
        │
        └─► POST /api/v1/games/sessions/end/
            {
              steam_app_id: 730,
              computer_id: 5,
              hours_played: 2.5
            }
            └─► Backend updates session
                └─► Sets session_status = ENDED
                    Sets current_session_start = null
                    Adds final hours to total_hours_played
```

### 5. Heartbeat Flow

```
Background Timer (every 30 seconds)
    │
    └─► POST /api/v1/computers/{id}/heartbeat/
        └─► Backend updates:
            ├─ computer.status = ONLINE
            └─ computer.last_seen = now()
```

---

## Security Architecture

### Authentication

- **JWT (JSON Web Tokens)** for stateless authentication
- Access token: Short-lived (15-30 minutes)
- Refresh token: Long-lived (7-30 days)

### Authorization

- **Role-based access control**:
  - Users: Can only access their own sessions and data
  - Staff: Can manage games and view all computers
  - Admin: Full system access

### PC Security

1. **Hardware ID**: Unique, persistent identifier
   - Prevents PC impersonation
   - Allows tracking across sessions

2. **Admin Privileges**: C# app runs as administrator
   - Prevents unauthorized closure
   - Controls game launching
   - Restricts system access

3. **Kiosk Mode**: Locks down the PC
   - Disables Alt+Tab
   - Blocks Task Manager
   - Prevents Windows key access

### API Security

- **HTTPS only** for production
- **CORS** configured for trusted origins
- **Rate limiting** (optional, can be added)
- **Input validation** on all endpoints

---

## Deployment Architecture

### Development Setup

```
┌─────────────────────────┐
│   Development Machine   │
│                         │
│  ┌──────────────────┐   │
│  │  Django Server   │   │
│  │  localhost:8000  │   │
│  └──────────────────┘   │
│                         │
│  ┌──────────────────┐   │
│  │   PostgreSQL     │   │
│  │  localhost:5432  │   │
│  └──────────────────┘   │
└─────────────────────────┘
```

### Production Setup

```
┌──────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
│                  (Nginx / Cloud LB)                      │
└────────────────────┬─────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌─────────────────┐
│   Web Server 1  │      │   Web Server 2  │
│                 │      │                 │
│  Django+Gunicorn│      │  Django+Gunicorn│
└────────┬────────┘      └────────┬────────┘
         │                        │
         └───────────┬────────────┘
                     │
         ┌───────────▼────────────┐
         │                        │
         │  PostgreSQL Database   │
         │   (RDS / Managed DB)   │
         │                        │
         └────────────────────────┘

┌──────────────────────────────────┐
│       Static Files (S3/CDN)      │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│   Celery Workers (Optional)      │
│   - Background tasks             │
│   - Session cleanup              │
│   - Statistics generation        │
└──────────────────────────────────┘
```

### Recommended Production Stack

- **Web Server**: Gunicorn + Nginx
- **Database**: PostgreSQL 13+
- **Caching**: Redis (optional)
- **Task Queue**: Celery + Redis (optional)
- **Hosting**: AWS, DigitalOcean, or similar
- **SSL/TLS**: Let's Encrypt or AWS Certificate Manager

---

## Scalability Considerations

### Horizontal Scaling

- **Stateless API**: Each request is independent (JWT tokens)
- **Load Balancing**: Can run multiple Django instances
- **Database Replication**: Read replicas for queries
- **Session Storage**: Can use Redis for session caching

### Performance Optimization

1. **Database Indexing**:
   - hardware_id, steam_app_id, account+game+computer
   - Indexes already defined in models

2. **Query Optimization**:
   - Use `select_related()` and `prefetch_related()`
   - Implement pagination for large lists

3. **Caching**:
   - Cache game library (rarely changes)
   - Cache user statistics (update periodically)
   - Use Redis for session data

4. **API Optimization**:
   - Compress responses (gzip)
   - Implement ETags for caching
   - Rate limiting to prevent abuse

---

## Monitoring and Logging

### Recommended Monitoring

1. **Application Monitoring**:
   - Track API response times
   - Monitor error rates
   - Log authentication attempts

2. **System Monitoring**:
   - PC heartbeat status
   - Active sessions count
   - Database performance

3. **Business Metrics**:
   - Total gaming hours
   - Most popular games
   - Peak usage times
   - Revenue tracking (if applicable)

### Logging Strategy

- **Application Logs**: Django logging framework
- **Access Logs**: Nginx/Gunicorn access logs
- **Error Logs**: Sentry or similar error tracking
- **Audit Logs**: Track admin actions and changes

---

## Future Enhancements

### Potential Features

1. **Real-time Communication**:
   - WebSockets for live updates
   - Chat between users
   - Admin announcements

2. **Advanced Analytics**:
   - Detailed usage reports
   - Revenue tracking
   - Game popularity trends

3. **Mobile App**:
   - View statistics on mobile
   - Reserve gaming time
   - Remote account management

4. **Payment Integration**:
   - Hourly billing
   - Game purchase/rental
   - Subscription plans

5. **Advanced PC Management**:
   - Remote PC control
   - Software deployment
   - Performance monitoring
   - Screenshot capture

---

## Conclusion

The PCHub system provides a robust, scalable architecture for managing gaming clubs and internet cafés. The combination of a Django backend and C# desktop application ensures reliable PC tracking, user management, and session monitoring.

For implementation details, refer to:
- [C# Integration Guide](./CSharp-Integration-Guide.md)
- [API Reference](./API-Reference.md)
