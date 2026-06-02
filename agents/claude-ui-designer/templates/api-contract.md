# API Contract - {Project Name}

## Overview

- **Project**: {Project Name}
- **Version**: 1.0.0
- **Created**: {Date}
- **Frontend Contact**: {Designer Name}
- **Backend Contact**: {Backend Dev Name}

## Base Configuration

```
Base URL: /api/v1
Content-Type: application/json
Authentication: Bearer Token (JWT)
```

---

## Data Models

### User

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | Unique identifier |
| phone | string | Yes | Phone number (11 digits) |
| nickname | string | No | Display name |
| avatar | string (URL) | No | Avatar image URL |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

### Auth

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| access_token | string | Yes | JWT access token |
| token_type | string | Yes | Token type (Bearer) |
| expires_in | integer | Yes | Expiration time in seconds |
| refresh_token | string | Yes | Refresh token for token renewal |

---

## API Endpoints

### Authentication

#### POST /auth/send-code
Send verification code to phone number.

**Request:**
```json
{
  "phone": "string"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Verification code sent",
  "data": {
    "expires_in": 300
  }
}
```

**Error Responses:**
| Code | Message | Description |
|------|---------|-------------|
| 400 | Invalid phone format | Phone number validation failed |
| 429 | Too many requests | Rate limit exceeded |
| 500 | Server error | Internal server error |

---

#### POST /auth/verify
Verify phone number with code and login/register.

**Request:**
```json
{
  "phone": "string",
  "code": "string"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "uuid",
      "phone": "string",
      "nickname": "string",
      "avatar": "string"
    },
    "auth": {
      "access_token": "string",
      "token_type": "Bearer",
      "expires_in": 7200,
      "refresh_token": "string"
    }
  }
}
```

**Error Responses:**
| Code | Message | Description |
|------|---------|-------------|
| 400 | Invalid verification code | Code incorrect or expired |
| 400 | Invalid phone format | Phone number validation failed |
| 500 | Server error | Internal server error |

---

#### POST /auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "string"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "access_token": "string",
    "token_type": "Bearer",
    "expires_in": 7200
  }
}
```

---

#### POST /auth/logout
Logout current user.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Logout successful"
}
```

---

## Common Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {} // Optional additional info
  }
}
```

### Standard Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| INVALID_PARAMS | 400 | Request parameter validation failed |
| INVALID_PHONE | 400 | Phone number format invalid |
| INVALID_CODE | 400 | Verification code invalid or expired |
| UNAUTHORIZED | 401 | Authentication required or token invalid |
| TOKEN_EXPIRED | 401 | Access token has expired |
| FORBIDDEN | 403 | Access denied |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMIT | 429 | Too many requests |
| SERVER_ERROR | 500 | Internal server error |

---

## Frontend Requirements

### Authentication Flow

1. User enters phone number
2. Frontend validates phone format (regex: `^1[3-9]\d{9}$`)
3. Call `/auth/send-code` to request verification code
4. Display countdown timer (60 seconds)
5. User enters 6-digit code
6. Call `/auth/verify` to login
7. Store `access_token` and `refresh_token` securely
8. Include `Authorization: Bearer {token}` in subsequent API calls

### Token Management

- Store tokens in secure storage (httpOnly cookie or secure localStorage)
- Refresh token before expiration (recommended: refresh when 5 minutes remaining)
- Clear tokens on logout

### Error Handling

- Display user-friendly error messages (not technical details)
- Show toast/alert for validation errors
- Redirect to login when `UNAUTHORIZED` or `TOKEN_EXPIRED`

---

## Mock Data Specification

For frontend development before backend is ready:

```typescript
// Mock data for /auth/verify
const mockUser = {
  id: "550e8400-e29b-41d4-a716-446655440000",
  phone: "13800138000",
  nickname: "User",
  avatar: ""
};

const mockAuth = {
  access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  token_type: "Bearer",
  expires_in: 7200,
  refresh_token: "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
};
```

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | {Date} | {Name} | Initial version |