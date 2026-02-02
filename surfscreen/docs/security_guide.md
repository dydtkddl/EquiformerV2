# SurfScreen Security Guide

This guide covers authentication, authorization, and rate limiting for the SurfScreen API.

## Authentication

### API Key Authentication

API keys are the primary authentication method for programmatic access.

#### Generating API Keys

```python
from surfscreen.api.middleware import generate_api_key, hash_api_key

# Generate a new API key
api_key = generate_api_key(prefix="sk")  # e.g., sk_abc123...

# Hash for storage
key_hash = hash_api_key(api_key)
```

#### Using API Keys

Include in request header:

```http
GET /api/v1/jobs
X-API-Key: sk_your_api_key_here
```

### JWT Authentication (Optional)

For session-based authentication:

```http
GET /api/v1/jobs
Authorization: Bearer eyJhbGciOiJIUzI1...
```

## Authorization (RBAC)

### Roles

| Role     | Description     | Permissions           |
| -------- | --------------- | --------------------- |
| `admin`  | Full access     | All operations        |
| `user`   | Standard access | CRUD on own resources |
| `viewer` | Read-only       | GET operations only   |

### Using in Endpoints

```python
from surfscreen.api.middleware import require_auth, require_role, require_permission, UserRole

@app.get("/admin/users")
async def admin_only(user = Depends(require_role([UserRole.ADMIN]))):
    return {"message": "Admin access"}

@app.post("/jobs")
async def create_job(user = Depends(require_permission("jobs:create"))):
    return {"message": "Job created"}
```

## Rate Limiting

### Default Limits

| Plan       | Requests/Min | Requests/Hour | Requests/Day |
| ---------- | ------------ | ------------- | ------------ |
| Free       | 10           | 100           | 500          |
| Basic      | 30           | 500           | 5,000        |
| Pro        | 100          | 2,000         | 20,000       |
| Enterprise | 500          | 10,000        | 100,000      |

### Response Headers

```http
X-RateLimit-Remaining-Minute: 58
X-RateLimit-Remaining-Hour: 498
Retry-After: 60  # (when rate limited)
```

### Rate Limit Exceeded Response

```json
{
  "detail": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "limit_type": "minute",
  "retry_after": 45
}
```

### Per-Endpoint Rate Limiting

```python
from surfscreen.api.middleware import rate_limit

@app.post("/expensive-operation")
async def expensive_op(
    _: None = Depends(rate_limit(requests_per_minute=5)),
):
    return {"result": "success"}
```

## Webhook Security

### HMAC Signatures

All webhook payloads are signed using HMAC-SHA256:

```python
import hmac
import hashlib
import json

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Signature Header

Webhooks include the signature in headers:

```http
X-SurfScreen-Signature: sha256=abc123...
X-SurfScreen-Timestamp: 1234567890
```

### Signature Verification Example

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    payload = request.get_data()
    signature = request.headers.get("X-SurfScreen-Signature", "").replace("sha256=", "")

    if not verify_webhook(payload, signature, WEBHOOK_SECRET):
        return "Invalid signature", 401

    data = json.loads(payload)
    # Process webhook...
    return "OK", 200
```

## Best Practices

### API Key Management

1. **Rotate keys regularly** - Use `/api/v1/users/{user_id}/api-keys` to manage keys
2. **Use scoped keys** - Create keys with minimal required permissions
3. **Never commit keys** - Use environment variables

### Rate Limit Handling

1. **Implement exponential backoff** when rate limited
2. **Cache responses** where possible
3. **Monitor usage** via rate limit headers

### Webhook Security

1. **Always verify signatures** before processing
2. **Validate timestamps** to prevent replay attacks
3. **Use HTTPS** for webhook endpoints

## Configuration

### Environment Variables

```bash
# JWT Configuration
SURFSCREEN_JWT_SECRET=your-secret-key
SURFSCREEN_JWT_ALGORITHM=HS256
SURFSCREEN_JWT_EXPIRE_HOURS=24

# Rate Limiting
SURFSCREEN_RATE_LIMIT_PLAN=pro
SURFSCREEN_RATE_LIMIT_ENABLED=true
```

### Middleware Registration

Middleware is automatically registered in `main.py`:

```python
from surfscreen.api.middleware import AuthenticationMiddleware, RateLimitMiddleware

app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware)
```
