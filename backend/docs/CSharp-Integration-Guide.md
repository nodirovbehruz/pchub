# C# Desktop Application Integration Guide

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Initial Setup and Installation](#initial-setup-and-installation)
4. [Hardware ID Generation](#hardware-id-generation)
5. [Authentication Flow](#authentication-flow)
6. [PC Registration](#pc-registration)
7. [User Login](#user-login)
8. [Game Management](#game-management)
9. [Session Tracking](#session-tracking)
10. [Heartbeat System](#heartbeat-system)
11. [Complete Implementation Example](#complete-implementation-example)

---

## Overview

This document provides comprehensive guidelines for integrating a C# desktop application with the PCHub Backend API for gaming club/internet café management.

### Key Requirements

- The C# application must run with **administrator privileges**
- Users cannot close the application unless authorized
- Each PC must generate a **unique hardware identifier**
- The app must track game sessions and report them to the backend
- Users see a dashboard with their gaming statistics upon login

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     C# Desktop Application                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  1. Hardware ID Generation (on first run)            │  │
│  │  2. PC Registration with Backend                     │  │
│  │  3. User Authentication                              │  │
│  │  4. Display Dashboard (stats, games)                 │  │
│  │  5. Game Selection and Launch                        │  │
│  │  6. Session Tracking                                 │  │
│  │  7. Heartbeat (every 30 seconds)                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↕ ️HTTP/HTTPS
┌─────────────────────────────────────────────────────────────┐
│                    PCHub Backend API                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Django REST Framework                               │  │
│  │  - Computer Management                               │  │
│  │  - Game Library                                      │  │
│  │  - Session Tracking                                  │  │
│  │  - User Statistics                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Initial Setup and Installation

### Prerequisites

Your C# application should:

1. Target **.NET Framework 4.8+** or **.NET 6.0+**
2. Use **HttpClient** for API communication
3. Run with **administrator privileges**
4. Implement **kiosk mode** to prevent users from exiting

### Recommended NuGet Packages

```xml
<PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
<PackageReference Include="System.Management" Version="7.0.0" />
```

---

## Hardware ID Generation

### Purpose

Each PC must have a unique, persistent identifier that doesn't change even if the computer name or IP changes. This identifier is used to track the PC across sessions.

### Implementation

The hardware ID should be a combination of:
- **CPU ID** (Processor Identifier)
- **Motherboard Serial Number**
- **Primary MAC Address**

**DO NOT regenerate this ID** once it's created. Store it in a local configuration file.

### C# Code Example

```csharp
using System;
using System.Management;
using System.Security.Cryptography;
using System.Text;
using System.IO;
using Newtonsoft.Json;

public class HardwareIdManager
{
    private const string CONFIG_FILE = "pc_config.json";

    public class PCConfig
    {
        public string HardwareId { get; set; }
        public int? ComputerId { get; set; }
        public DateTime? LastRegistered { get; set; }
    }

    /// <summary>
    /// Get or generate hardware ID for this PC
    /// </summary>
    public static string GetHardwareId()
    {
        // Check if config file exists
        if (File.Exists(CONFIG_FILE))
        {
            try
            {
                string json = File.ReadAllText(CONFIG_FILE);
                var config = JsonConvert.DeserializeObject<PCConfig>(json);

                if (!string.IsNullOrEmpty(config.HardwareId))
                {
                    return config.HardwareId;
                }
            }
            catch
            {
                // If file is corrupted, regenerate
            }
        }

        // Generate new hardware ID
        string hwid = GenerateHardwareId();

        // Save to config file
        var newConfig = new PCConfig
        {
            HardwareId = hwid,
            LastRegistered = null
        };

        File.WriteAllText(CONFIG_FILE, JsonConvert.SerializeObject(newConfig, Formatting.Indented));

        return hwid;
    }

    /// <summary>
    /// Generate unique hardware ID based on CPU, Motherboard, and MAC address
    /// </summary>
    private static string GenerateHardwareId()
    {
        string cpuId = GetCpuId();
        string motherboardId = GetMotherboardSerial();
        string macAddress = GetMacAddress();

        string combined = $"{cpuId}-{motherboardId}-{macAddress}";

        // Create SHA256 hash for consistent length
        using (SHA256 sha256 = SHA256.Create())
        {
            byte[] bytes = sha256.ComputeHash(Encoding.UTF8.GetBytes(combined));
            StringBuilder builder = new StringBuilder();

            foreach (byte b in bytes)
            {
                builder.Append(b.ToString("x2"));
            }

            return builder.ToString().Substring(0, 64); // First 64 characters
        }
    }

    private static string GetCpuId()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT ProcessorId FROM Win32_Processor");

            foreach (ManagementObject obj in searcher.Get())
            {
                return obj["ProcessorId"]?.ToString() ?? "UNKNOWN_CPU";
            }
        }
        catch
        {
            return "UNKNOWN_CPU";
        }

        return "UNKNOWN_CPU";
    }

    private static string GetMotherboardSerial()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT SerialNumber FROM Win32_BaseBoard");

            foreach (ManagementObject obj in searcher.Get())
            {
                return obj["SerialNumber"]?.ToString() ?? "UNKNOWN_MB";
            }
        }
        catch
        {
            return "UNKNOWN_MB";
        }

        return "UNKNOWN_MB";
    }

    private static string GetMacAddress()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT MACAddress FROM Win32_NetworkAdapter WHERE MACAddress IS NOT NULL");

            foreach (ManagementObject obj in searcher.Get())
            {
                string mac = obj["MACAddress"]?.ToString();
                if (!string.IsNullOrEmpty(mac) && mac != "00:00:00:00:00:00")
                {
                    return mac.Replace(":", "");
                }
            }
        }
        catch
        {
            return "UNKNOWN_MAC";
        }

        return "UNKNOWN_MAC";
    }

    /// <summary>
    /// Save computer ID after registration
    /// </summary>
    public static void SaveComputerId(int computerId)
    {
        var config = new PCConfig
        {
            HardwareId = GetHardwareId(),
            ComputerId = computerId,
            LastRegistered = DateTime.Now
        };

        File.WriteAllText(CONFIG_FILE, JsonConvert.SerializeObject(config, Formatting.Indented));
    }

    /// <summary>
    /// Get saved computer ID
    /// </summary>
    public static int? GetComputerId()
    {
        if (File.Exists(CONFIG_FILE))
        {
            try
            {
                string json = File.ReadAllText(CONFIG_FILE);
                var config = JsonConvert.DeserializeObject<PCConfig>(json);
                return config.ComputerId;
            }
            catch
            {
                return null;
            }
        }

        return null;
    }
}
```

### Important Notes

- **Never regenerate the hardware ID** after initial generation
- Store the hardware ID in a **protected configuration file** (e.g., `pc_config.json`)
- If the configuration file is deleted, the PC will be registered as a new computer

---

## Authentication Flow

### User Authentication with Backend

Users authenticate using **username and password**. The backend uses **JWT tokens** or **session-based authentication**.

### C# Code Example

```csharp
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class ApiClient
{
    private static readonly HttpClient client = new HttpClient();
    private const string BASE_URL = "https://your-backend-url.com/api/v1";
    private static string authToken = null;

    public class LoginRequest
    {
        [JsonProperty("username")]
        public string Username { get; set; }

        [JsonProperty("password")]
        public string Password { get; set; }
    }

    public class LoginResponse
    {
        [JsonProperty("access")]
        public string AccessToken { get; set; }

        [JsonProperty("refresh")]
        public string RefreshToken { get; set; }

        [JsonProperty("user")]
        public UserInfo User { get; set; }
    }

    public class UserInfo
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("username")]
        public string Username { get; set; }

        [JsonProperty("email")]
        public string Email { get; set; }
    }

    /// <summary>
    /// Authenticate user with backend
    /// </summary>
    public static async Task<LoginResponse> LoginAsync(string username, string password)
    {
        var loginData = new LoginRequest
        {
            Username = username,
            Password = password
        };

        string json = JsonConvert.SerializeObject(loginData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpResponseMessage response = await client.PostAsync($"{BASE_URL}/accounts/login/", content);

        if (response.IsSuccessStatusCode)
        {
            string responseBody = await response.Content.ReadAsStringAsync();
            var loginResponse = JsonConvert.DeserializeObject<LoginResponse>(responseBody);

            // Save auth token
            authToken = loginResponse.AccessToken;

            // Set default authorization header
            client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", authToken);

            return loginResponse;
        }
        else
        {
            string error = await response.Content.ReadAsStringAsync();
            throw new Exception($"Login failed: {error}");
        }
    }

    /// <summary>
    /// Set auth token for API calls
    /// </summary>
    public static void SetAuthToken(string token)
    {
        authToken = token;
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
    }
}
```

### Login Endpoint

- **URL**: `POST /api/v1/accounts/login/`
- **Request Body**:
  ```json
  {
    "username": "user123",
    "password": "password123"
  }
  ```
- **Response**:
  ```json
  {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {
      "id": 1,
      "username": "user123",
      "email": "user@example.com"
    }
  }
  ```

---

## PC Registration

### When to Register

- **On first launch**: If no `pc_config.json` exists
- **On every launch**: To update PC specs and status

### C# Code Example

```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Management;
using Newtonsoft.Json;

public class ComputerRegistration
{
    public class RegisterRequest
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("hardware_id")]
        public string HardwareId { get; set; }

        [JsonProperty("description")]
        public string Description { get; set; }

        [JsonProperty("cpu_model")]
        public string CpuModel { get; set; }

        [JsonProperty("cpu_cores")]
        public int CpuCores { get; set; }

        [JsonProperty("cpu_threads")]
        public int CpuThreads { get; set; }

        [JsonProperty("ram_total_gb")]
        public decimal RamTotalGb { get; set; }

        [JsonProperty("gpu_model")]
        public string GpuModel { get; set; }

        [JsonProperty("storage_total_gb")]
        public decimal StorageTotalGb { get; set; }

        [JsonProperty("os_name")]
        public string OsName { get; set; }

        [JsonProperty("os_version")]
        public string OsVersion { get; set; }

        [JsonProperty("ip_address")]
        public string IpAddress { get; set; }

        [JsonProperty("mac_address")]
        public string MacAddress { get; set; }
    }

    public class RegisterResponse
    {
        [JsonProperty("id")]
        public int Id { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("hardware_id")]
        public string HardwareId { get; set; }

        [JsonProperty("status")]
        public string Status { get; set; }
    }

    /// <summary>
    /// Register this PC with the backend
    /// </summary>
    public static async Task<RegisterResponse> RegisterPCAsync()
    {
        string hardwareId = HardwareIdManager.GetHardwareId();

        var registerData = new RegisterRequest
        {
            Name = Environment.MachineName,
            HardwareId = hardwareId,
            Description = $"Gaming PC - {Environment.MachineName}",
            CpuModel = GetCpuModel(),
            CpuCores = Environment.ProcessorCount,
            CpuThreads = Environment.ProcessorCount,
            RamTotalGb = GetTotalRamGB(),
            GpuModel = GetGpuModel(),
            StorageTotalGb = GetTotalStorageGB(),
            OsName = "Windows",
            OsVersion = Environment.OSVersion.Version.ToString(),
            IpAddress = GetLocalIPAddress(),
            MacAddress = GetMacAddress()
        };

        string json = JsonConvert.SerializeObject(registerData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpClient client = new HttpClient();
        client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", ApiClient.authToken);

        HttpResponseMessage response = await client.PostAsync("https://your-backend-url.com/api/v1/computers/register/", content);

        if (response.IsSuccessStatusCode)
        {
            string responseBody = await response.Content.ReadAsStringAsync();
            var registerResponse = JsonConvert.DeserializeObject<RegisterResponse>(responseBody);

            // Save computer ID
            HardwareIdManager.SaveComputerId(registerResponse.Id);

            return registerResponse;
        }
        else
        {
            string error = await response.Content.ReadAsStringAsync();
            throw new Exception($"PC registration failed: {error}");
        }
    }

    // Helper methods to get system info
    private static string GetCpuModel()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT Name FROM Win32_Processor");
            foreach (ManagementObject obj in searcher.Get())
            {
                return obj["Name"]?.ToString() ?? "Unknown CPU";
            }
        }
        catch { }
        return "Unknown CPU";
    }

    private static decimal GetTotalRamGB()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT TotalPhysicalMemory FROM Win32_ComputerSystem");
            foreach (ManagementObject obj in searcher.Get())
            {
                ulong bytes = (ulong)obj["TotalPhysicalMemory"];
                return (decimal)(bytes / 1024.0 / 1024.0 / 1024.0);
            }
        }
        catch { }
        return 0;
    }

    private static string GetGpuModel()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT Name FROM Win32_VideoController");
            foreach (ManagementObject obj in searcher.Get())
            {
                return obj["Name"]?.ToString() ?? "Unknown GPU";
            }
        }
        catch { }
        return "Unknown GPU";
    }

    private static decimal GetTotalStorageGB()
    {
        try
        {
            long totalBytes = 0;
            foreach (var drive in System.IO.DriveInfo.GetDrives())
            {
                if (drive.IsReady)
                {
                    totalBytes += drive.TotalSize;
                }
            }
            return (decimal)(totalBytes / 1024.0 / 1024.0 / 1024.0);
        }
        catch { }
        return 0;
    }

    private static string GetLocalIPAddress()
    {
        try
        {
            var host = System.Net.Dns.GetHostEntry(System.Net.Dns.GetHostName());
            foreach (var ip in host.AddressList)
            {
                if (ip.AddressFamily == System.Net.Sockets.AddressFamily.InterNetwork)
                {
                    return ip.ToString();
                }
            }
        }
        catch { }
        return "127.0.0.1";
    }

    private static string GetMacAddress()
    {
        try
        {
            ManagementObjectSearcher searcher = new ManagementObjectSearcher("SELECT MACAddress FROM Win32_NetworkAdapter WHERE MACAddress IS NOT NULL");
            foreach (ManagementObject obj in searcher.Get())
            {
                string mac = obj["MACAddress"]?.ToString();
                if (!string.IsNullOrEmpty(mac) && mac != "00:00:00:00:00:00")
                {
                    return mac;
                }
            }
        }
        catch { }
        return "00:00:00:00:00:00";
    }
}
```

### Registration Endpoint

- **URL**: `POST /api/v1/computers/register/`
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**: See `RegisterRequest` class above
- **Response**: Returns computer object with ID

### Important Behavior

- If a computer with the same `hardware_id` already exists, the backend will **update** its information instead of creating a new record
- This allows the same PC to re-register without creating duplicates

---

## User Login

After PC registration, the user logs in to see their dashboard.

### Dashboard Endpoint

- **URL**: `GET /api/v1/games/dashboard/`
- **Headers**: `Authorization: Bearer {token}`
- **Response**:
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
        "game": {
          "id": 10,
          "steam_app_id": 730,
          "name": "Counter-Strike 2",
          "icon_url": "https://..."
        },
        "total_hours_played": 45.5,
        "last_played": "2025-12-20T10:30:00Z"
      }
    ],
    "recent_sessions": [...],
    "active_session": null
  }
  ```

### C# Code Example

```csharp
public class DashboardData
{
    [JsonProperty("user")]
    public UserInfo User { get; set; }

    [JsonProperty("statistics")]
    public Statistics Stats { get; set; }

    [JsonProperty("most_played_games")]
    public List<GameSession> MostPlayedGames { get; set; }

    [JsonProperty("recent_sessions")]
    public List<GameSession> RecentSessions { get; set; }

    [JsonProperty("active_session")]
    public GameSession ActiveSession { get; set; }
}

public class Statistics
{
    [JsonProperty("total_hours_played")]
    public double TotalHoursPlayed { get; set; }

    [JsonProperty("total_games")]
    public int TotalGames { get; set; }

    [JsonProperty("total_sessions")]
    public int TotalSessions { get; set; }
}

public class GameSession
{
    [JsonProperty("id")]
    public int Id { get; set; }

    [JsonProperty("game")]
    public GameInfo Game { get; set; }

    [JsonProperty("total_hours_played")]
    public double TotalHoursPlayed { get; set; }

    [JsonProperty("last_played")]
    public DateTime LastPlayed { get; set; }
}

public class GameInfo
{
    [JsonProperty("id")]
    public int Id { get; set; }

    [JsonProperty("steam_app_id")]
    public int SteamAppId { get; set; }

    [JsonProperty("name")]
    public string Name { get; set; }

    [JsonProperty("icon_url")]
    public string IconUrl { get; set; }
}

public static async Task<DashboardData> GetDashboardAsync()
{
    HttpClient client = new HttpClient();
    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", authToken);

    HttpResponseMessage response = await client.GetAsync("https://your-backend-url.com/api/v1/games/dashboard/");

    if (response.IsSuccessStatusCode)
    {
        string responseBody = await response.Content.ReadAsStringAsync();
        return JsonConvert.DeserializeObject<DashboardData>(responseBody);
    }
    else
    {
        throw new Exception("Failed to load dashboard");
    }
}
```

---

## Game Management

### Get Available Games on This PC

Before showing the game selection menu, fetch the list of games installed on this PC.

- **URL**: `GET /api/v1/games/computer/games/?hardware_id={hardware_id}`
- **Headers**: `Authorization: Bearer {token}`
- **Response**:
  ```json
  {
    "computer": {
      "id": 5,
      "name": "Gaming-PC-01",
      "hardware_id": "abc123..."
    },
    "games": [
      {
        "id": 10,
        "steam_app_id": 730,
        "name": "Counter-Strike 2",
        "icon_url": "https://...",
        "developer": "Valve"
      }
    ],
    "total_games": 1
  }
  ```

### C# Code Example

```csharp
public class ComputerGamesResponse
{
    [JsonProperty("computer")]
    public ComputerInfo Computer { get; set; }

    [JsonProperty("games")]
    public List<GameInfo> Games { get; set; }

    [JsonProperty("total_games")]
    public int TotalGames { get; set; }
}

public class ComputerInfo
{
    [JsonProperty("id")]
    public int Id { get; set; }

    [JsonProperty("name")]
    public string Name { get; set; }

    [JsonProperty("hardware_id")]
    public string HardwareId { get; set; }
}

public static async Task<ComputerGamesResponse> GetComputerGamesAsync()
{
    string hardwareId = HardwareIdManager.GetHardwareId();

    HttpClient client = new HttpClient();
    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", authToken);

    HttpResponseMessage response = await client.GetAsync($"https://your-backend-url.com/api/v1/games/computer/games/?hardware_id={hardwareId}");

    if (response.IsSuccessStatusCode)
    {
        string responseBody = await response.Content.ReadAsStringAsync();
        return JsonConvert.DeserializeObject<ComputerGamesResponse>(responseBody);
    }
    else
    {
        throw new Exception("Failed to load games");
    }
}
```

---

## Session Tracking

### Session Lifecycle

1. **Start Session**: When user selects a game and it launches
2. **Update Session**: Periodically (every 5-10 minutes) while game is running
3. **End Session**: When game closes

### Start Session

- **URL**: `POST /api/v1/games/sessions/start/`
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**:
  ```json
  {
    "steam_app_id": 730,
    "computer_id": 5,
    "game_name": "Counter-Strike 2"
  }
  ```

### Update Session (Add Hours)

- **URL**: `POST /api/v1/games/sessions/update/`
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**:
  ```json
  {
    "steam_app_id": 730,
    "computer_id": 5,
    "hours_to_add": 0.1
  }
  ```

### End Session

- **URL**: `POST /api/v1/games/sessions/end/`
- **Headers**: `Authorization: Bearer {token}`
- **Request Body**:
  ```json
  {
    "steam_app_id": 730,
    "computer_id": 5,
    "hours_played": 2.5
  }
  ```

### C# Code Example

```csharp
public class SessionManager
{
    private static System.Timers.Timer sessionTimer;
    private static DateTime sessionStartTime;
    private static int currentSteamAppId;
    private static int computerId;

    public static async Task StartSessionAsync(int steamAppId, string gameName)
    {
        computerId = HardwareIdManager.GetComputerId() ?? 0;
        currentSteamAppId = steamAppId;
        sessionStartTime = DateTime.Now;

        var request = new
        {
            steam_app_id = steamAppId,
            computer_id = computerId,
            game_name = gameName
        };

        string json = JsonConvert.SerializeObject(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpClient client = new HttpClient();
        client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", ApiClient.authToken);

        await client.PostAsync("https://your-backend-url.com/api/v1/games/sessions/start/", content);

        // Start periodic update timer (every 5 minutes)
        sessionTimer = new System.Timers.Timer(5 * 60 * 1000);
        sessionTimer.Elapsed += async (sender, e) => await UpdateSessionAsync();
        sessionTimer.Start();
    }

    private static async Task UpdateSessionAsync()
    {
        double hoursPlayed = (DateTime.Now - sessionStartTime).TotalHours;

        var request = new
        {
            steam_app_id = currentSteamAppId,
            computer_id = computerId,
            hours_to_add = Math.Round(hoursPlayed, 2)
        };

        string json = JsonConvert.SerializeObject(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpClient client = new HttpClient();
        client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", ApiClient.authToken);

        await client.PostAsync("https://your-backend-url.com/api/v1/games/sessions/update/", content);

        // Reset start time
        sessionStartTime = DateTime.Now;
    }

    public static async Task EndSessionAsync()
    {
        if (sessionTimer != null)
        {
            sessionTimer.Stop();
            sessionTimer.Dispose();
        }

        double hoursPlayed = (DateTime.Now - sessionStartTime).TotalHours;

        var request = new
        {
            steam_app_id = currentSteamAppId,
            computer_id = computerId,
            hours_played = Math.Round(hoursPlayed, 2)
        };

        string json = JsonConvert.SerializeObject(request);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        HttpClient client = new HttpClient();
        client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", ApiClient.authToken);

        await client.PostAsync("https://your-backend-url.com/api/v1/games/sessions/end/", content);
    }
}
```

---

## Heartbeat System

The C# app should send a heartbeat every 30 seconds to keep the PC status as `ONLINE`.

- **URL**: `POST /api/v1/computers/{computer_id}/heartbeat/`
- **Headers**: `Authorization: Bearer {token}`

### C# Code Example

```csharp
public class HeartbeatManager
{
    private static System.Timers.Timer heartbeatTimer;

    public static void StartHeartbeat()
    {
        int? computerId = HardwareIdManager.GetComputerId();
        if (!computerId.HasValue) return;

        heartbeatTimer = new System.Timers.Timer(30 * 1000); // 30 seconds
        heartbeatTimer.Elapsed += async (sender, e) => await SendHeartbeatAsync(computerId.Value);
        heartbeatTimer.Start();

        // Send initial heartbeat
        Task.Run(async () => await SendHeartbeatAsync(computerId.Value));
    }

    private static async Task SendHeartbeatAsync(int computerId)
    {
        try
        {
            HttpClient client = new HttpClient();
            client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", ApiClient.authToken);

            var content = new StringContent("{}", Encoding.UTF8, "application/json");
            await client.PostAsync($"https://your-backend-url.com/api/v1/computers/{computerId}/heartbeat/", content);
        }
        catch
        {
            // Log error
        }
    }

    public static void StopHeartbeat()
    {
        heartbeatTimer?.Stop();
        heartbeatTimer?.Dispose();
    }
}
```

---

## Complete Implementation Example

### Main Application Flow

```csharp
public class Program
{
    [STAThread]
    static async Task Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        try
        {
            // Step 1: Get/Generate Hardware ID
            string hardwareId = HardwareIdManager.GetHardwareId();
            Console.WriteLine($"Hardware ID: {hardwareId}");

            // Step 2: Show login form
            LoginForm loginForm = new LoginForm();
            if (loginForm.ShowDialog() != DialogResult.OK)
            {
                return; // User cancelled login
            }

            string username = loginForm.Username;
            string password = loginForm.Password;

            // Step 3: Authenticate with backend
            var loginResponse = await ApiClient.LoginAsync(username, password);
            Console.WriteLine($"Logged in as: {loginResponse.User.Username}");

            // Step 4: Register/Update PC
            await ComputerRegistration.RegisterPCAsync();
            Console.WriteLine("PC registered");

            // Step 5: Start heartbeat
            HeartbeatManager.StartHeartbeat();

            // Step 6: Load dashboard
            var dashboardData = await GetDashboardAsync();

            // Step 7: Show main form
            MainForm mainForm = new MainForm(dashboardData);
            Application.Run(mainForm);

            // Cleanup
            HeartbeatManager.StopHeartbeat();
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Error: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
```

---

## Security Considerations

1. **Admin Privileges**: The app must run as administrator to:
   - Prevent users from closing it
   - Access hardware information
   - Control game launches

2. **Kiosk Mode**: Implement full-screen kiosk mode to prevent:
   - Alt+Tab switching
   - Windows key access
   - Task Manager access
   - Unauthorized app closure

3. **Secure Token Storage**: Store JWT tokens securely in memory, not in plain text files

4. **HTTPS Only**: Always use HTTPS for API communication

---

## Troubleshooting

### PC Not Registering

- Check that `hardware_id` is being generated correctly
- Ensure user is authenticated before registration
- Verify network connectivity

### Sessions Not Tracking

- Confirm computer is registered and has valid `computer_id`
- Check that session start/update/end are called at correct times
- Verify authentication token is valid

### Heartbeat Not Working

- Ensure heartbeat timer is started after PC registration
- Check that computer_id is saved and retrieved correctly
- Verify API endpoint is accessible

---

## Summary

This integration guide provides all the necessary information to build a C# desktop application that:

1. Generates a unique hardware ID for each PC
2. Registers the PC with the backend
3. Authenticates users
4. Displays user gaming statistics
5. Tracks game sessions
6. Maintains PC online status

For detailed API reference, see [API-Reference.md](./API-Reference.md).

For system architecture details, see [Architecture.md](./Architecture.md).
