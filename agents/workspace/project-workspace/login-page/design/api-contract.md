# Login Page API Contract

## Overview

- **Project**: Login Page
- **Version**: 1.0.0
- **Created**: 2026-05-19
- **Designer**: UI Designer Agent
- **Backend**: Backend Dev Agent

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
| phone | string | Yes | Phone number (11 digits, starts with 1) |
| nickname | string | No | Display name |
| avatar | string (URL) | No | Avatar image URL |
| created_at | datetime | Yes | Creation timestamp |
| updated_at | datetime | Yes | Last update timestamp |

### Auth

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| access_token | string | Yes | JWT access token |
| token_type | string | Yes | Token type (Bearer) |
| expires_in | integer | Yes | Expiration time in seconds (7200) |
| refresh_token | string | Yes | Refresh token for token renewal |

---

## API Endpoints

### Authentication

#### POST /api/v1/auth/send-code
Send verification code to phone number.

**Request:**
```json
{
  "phone": "13800138000"
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

**Validation:**
- phone: required, string, pattern `^1[3-9]\d{9}$`

**Error Responses:**
| Code | Message | Description |
|------|---------|-------------|
| INVALID_PHONE | Invalid phone format | Phone number validation failed |
| RATE_LIMIT | Too many requests | Rate limit exceeded (max 5/minute) |
| SERVER_ERROR | Server error | Internal server error |

---

#### POST /api/v1/auth/verify
Verify phone number with code and login/register.

**Request:**
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "phone": "13800138000",
      "nickname": "",
      "avatar": "",
      "created_at": "2026-05-19T10:30:00Z",
      "updated_at": "2026-05-19T10:30:00Z"
    },
    "auth": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 7200,
      "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
    }
  }
}
```

**Validation:**
- phone: required, string, pattern `^1[3-9]\d{9}$`
- code: required, string, 6 digits

**Error Responses:**
| Code | Message | Description |
|------|---------|-------------|
| INVALID_PARAMS | Invalid parameters | Request validation failed |
| INVALID_CODE | Verification code invalid or expired | Code incorrect or expired |
| SERVER_ERROR | Server error | Internal server error |

---

#### POST /api/v1/auth/refresh
Refresh access token.

**Request:**
```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4..."
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 7200
  }
}
```

**Error Responses:**
| Code | Message | Description |
|------|---------|-------------|
| INVALID_REFRESH_TOKEN | Refresh token invalid | Token expired or tampered |
| UNAUTHORIZED | Unauthorized | No token provided |

---

#### POST /api/v1/auth/logout
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

**Error Responses:**
| Code | Message | Description |
|------|---------|-------------|
| UNAUTHORIZED | Unauthorized | Invalid or missing token |

---

## Common Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
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
3. Call `/api/v1/auth/send-code` to request verification code
4. Display countdown timer (60 seconds)
5. User enters 6-digit code
6. Call `/api/v1/auth/verify` to login
7. Store `access_token` and `refresh_token` securely
8. Include `Authorization: Bearer {token}` in subsequent API calls

### Token Management

- Store tokens in secure storage
- Refresh token before expiration (recommended: refresh when 5 minutes remaining)
- Clear tokens on logout

### Error Handling

- Display user-friendly error messages
- Show inline validation errors for form fields
- Show toast for server errors
- Redirect to home/dashboard on successful login

---

## Mock Data Specification

For frontend development:

### POST /api/v1/auth/verify - Mock Response

**Request:**
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**Mock Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "phone": "13800138000",
      "nickname": "新用户",
      "avatar": "",
      "created_at": "2026-05-19T10:30:00Z",
      "updated_at": "2026-05-19T10:30:00Z"
    },
    "auth": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMzgwMDEzODAwMCIsImlhdCI6MTcwNTYxNjIwMCwiZXhwIjoxNzA1NzAyNjAwfQ.mock-signature",
      "token_type": "Bearer",
      "expires_in": 7200,
      "refresh_token": "mock-refresh-token-550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

---

## Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-05-19 | Designer Agent | Initial API contract for login page |