# Security Guide - PokeWatch API

Complete guide for API security, authentication, and rate limiting.

## Table of Contents

1. [Overview](#overview)
2. [API Key Authentication](#api-key-authentication)
3. [Rate Limiting](#rate-limiting)
4. [Security Middleware](#security-middleware)
5. [CORS Configuration](#cors-configuration)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

## Overview

PokeWatch API implements multiple layers of security:

- **Authentication**: API key-based authentication via `X-API-Key` header
- **Rate Limiting**: Token bucket algorithm limiting requests per minute
- **Security Headers**: OWASP-recommended HTTP security headers
- **CORS**: Configurable Cross-Origin Resource Sharing
- **Request Logging**: Comprehensive request/response logging with masking
- **Request Size Limits**: Protection against large payload attacks

### Security Architecture

```
Request → CORS Check → Request Size Limit → Request ID → Auth → Rate Limit → Endpoint
                                                ↓
                                    Security Headers Added
                                                ↓
                                         Logging & Monitoring
```

---

## API Key Authentication

### Overview

API keys provide simple, secure authentication for programmatic access to the API.

**Features:**
- Header-based authentication (`X-API-Key`)
- Support for multiple API keys
- Key rotation without downtime
- Optional authentication mode
- Secure key generation
- Key masking for logs

### Generating API Keys

#### Using the Management Script

```bash
cd pokewatch

# Generate and add new key
python scripts/manage_api_keys.py generate --add

# Output:
# ✓ Generated and added new API key: pk_abc123def456ghi789xyz
#   Total keys: 3
```

#### Programmatically

```python
from pokewatch.api.auth import generate_api_key

# Generate with default settings
api_key = generate_api_key()
# pk_XYZ123...

# Generate with custom prefix
api_key = generate_api_key(prefix="prod", length=32)
# prod_XYZ123...
```

### Managing API Keys

#### List All Keys

```bash
# List masked keys
python scripts/manage_api_keys.py list

# Output:
# API Keys (3):
# ------------------------------------------------------------
# 1. pk_***g7h8
# 2. pk_***x9y0
# 3. pk_***m3n4

# List full keys (be careful!)
python scripts/manage_api_keys.py list --show-full
```

#### Add Existing Key

```bash
python scripts/manage_api_keys.py add pk_existing_key_123
```

#### Revoke Key

```bash
# Revoke by full key
python scripts/manage_api_keys.py revoke pk_abc123def456

# Revoke by last characters
python scripts/manage_api_keys.py revoke f456
```

#### Rotate Key

```bash
python scripts/manage_api_keys.py rotate pk_old_key

# Output:
# ✓ Rotated API key
#   Old key: pk_***d_key (revoked)
#   New key: pk_new123abc456def789
#
# Update your clients with the new key!
```

### Configuration

#### Environment Variables

```bash
# Enable/disable authentication
AUTH_ENABLED=true

# API keys (comma-separated)
API_KEYS=pk_key1,pk_key2,pk_key3
```

#### settings.yaml

```yaml
api:
  auth:
    enabled: true
    require_api_key: true  # Set to false for testing
```

### Using API Keys

#### curl

```bash
curl -X POST https://api.pokewatch.com/fair_price \
  -H "X-API-Key: pk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"card_id": "sv4pt5-001", "date": "2024-01-15"}'
```

#### Python requests

```python
import requests

headers = {
    "X-API-Key": "pk_your_api_key_here",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.pokewatch.com/fair_price",
    headers=headers,
    json={"card_id": "sv4pt5-001", "date": "2024-01-15"}
)

print(response.json())
```

#### JavaScript fetch

```javascript
const response = await fetch('https://api.pokewatch.com/fair_price', {
  method: 'POST',
  headers: {
    'X-API-Key': 'pk_your_api_key_here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    card_id: 'sv4pt5-001',
    date: '2024-01-15'
  })
});

const data = await response.json();
console.log(data);
```

### Error Responses

#### Missing API Key (401)

```json
{
  "detail": "Missing API key. Provide X-API-Key header."
}
```

Response headers include:
```
WWW-Authenticate: ApiKey
```

#### Invalid API Key (401)

```json
{
  "detail": "Invalid API key"
}
```

### Optional Authentication

For development/testing, authentication can be made optional:

```python
# In code
from pokewatch.api.auth import APIKeyAuth

auth = APIKeyAuth(required=False)

# Or via environment
AUTH_ENABLED=false
```

When optional, requests without API keys will be logged as "anonymous".

---

## Rate Limiting

### Overview

Rate limiting prevents API abuse by limiting the number of requests per time window.

**Algorithm**: Token Bucket
**Features:**
- Per-API-key limiting
- Configurable requests per minute
- Burst handling
- Rate limit headers
- Redis backend for distributed systems

### Configuration

#### Environment Variables

```bash
# Enable/disable rate limiting
RATE_LIMIT_ENABLED=true

# Requests per minute (per key)
RATE_LIMIT_RPM=60

# Burst size (max tokens in bucket)
RATE_LIMIT_BURST=10

# Redis URL for distributed rate limiting
REDIS_URL=redis://localhost:6379
```

#### settings.yaml

```yaml
api:
  rate_limit:
    enabled: true
    requests_per_minute: 60
    burst_size: 10
```

### Rate Limit Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1699564800
```

- **X-RateLimit-Limit**: Maximum requests per minute
- **X-RateLimit-Remaining**: Requests remaining in current window
- **X-RateLimit-Reset**: Unix timestamp when limit resets

### Rate Limit Exceeded (429)

When rate limit is exceeded, you receive a `429 Too Many Requests` response:

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds."
}
```

Response headers include:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1699564830
Retry-After: 30
```

**Retry-After** header indicates seconds to wait before retrying.

### Handling Rate Limits

#### Python with exponential backoff

```python
import requests
import time

def make_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

#### JavaScript with retry

```javascript
async function makeRequestWithRetry(url, options, maxRetries = 3) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const response = await fetch(url, options);

    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
      console.log(`Rate limited. Waiting ${retryAfter} seconds...`);
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}
```

### Per-API-Key vs Per-IP

- **Authenticated requests**: Rate limited by API key
- **Unauthenticated requests**: Rate limited by IP address

This ensures fair usage across different clients.

### Distributed Rate Limiting

For multi-instance deployments, use Redis backend:

```bash
# Set Redis URL
export REDIS_URL=redis://redis:6379

# Rate limiter will automatically use Redis
```

Redis-backed rate limiting uses a sliding window algorithm for accurate limiting across multiple API instances.

---

## Security Middleware

### Request ID Tracking

Every request gets a unique ID for tracing:

```bash
# Request
curl https://api.pokewatch.com/health

# Response headers include:
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

Use request IDs for:
- Debugging specific requests
- Tracing requests across systems
- Correlating logs

### Request/Response Logging

All requests and responses are logged with:
- Request ID
- HTTP method and path
- API key (masked)
- Client IP address
- Response status code
- Duration

Example log:

```
2024-01-15 10:30:45 - INFO - Request started | ID: 550e8400-... | Method: POST | Path: /fair_price | API Key: pk_***h8i9 | Client: 192.168.1.100
2024-01-15 10:30:45 - INFO - Request completed | ID: 550e8400-... | Status: 200 | Duration: 0.123s
```

### Security Headers

All responses include OWASP-recommended security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()
```

For HTTPS connections:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### Request Size Limits

Maximum request size: **10 MB** (configurable)

Requests exceeding this limit receive a `413 Payload Too Large` response.

Configure via:

```python
from pokewatch.api.middleware import setup_middleware

setup_middleware(app, config={
    "max_request_size": 5 * 1024 * 1024  # 5 MB
})
```

---

## CORS Configuration

### Overview

Cross-Origin Resource Sharing (CORS) allows browser-based clients to access the API.

### Configuration

#### Environment Variables

```bash
# Enable CORS
CORS_ENABLED=true

# Allowed origins (comma-separated)
ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com

# Allow all origins (development only!)
ALLOWED_ORIGINS=*
```

#### settings.yaml

```yaml
api:
  security:
    cors_enabled: true
    allowed_origins:
      - "https://app.example.com"
      - "https://admin.example.com"
```

### CORS Headers

The API includes these CORS headers:

```
Access-Control-Allow-Origin: https://app.example.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: X-API-Key, Content-Type, X-Request-ID
Access-Control-Expose-Headers: X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining
Access-Control-Allow-Credentials: true
```

### Preflight Requests

The API automatically handles `OPTIONS` preflight requests for CORS.

---

## Best Practices

### 1. API Key Security

✅ **Do:**
- Store API keys in environment variables
- Use different keys for dev/staging/production
- Rotate keys regularly (every 90 days)
- Use HTTPS for all API requests
- Keep keys out of version control

❌ **Don't:**
- Hardcode API keys in source code
- Share API keys between environments
- Expose keys in client-side code
- Commit keys to git repositories
- Use the same key for all clients

### 2. Rate Limiting

✅ **Do:**
- Implement exponential backoff on 429 responses
- Monitor rate limit headers
- Cache responses when possible
- Use batch endpoints for multiple requests

❌ **Don't:**
- Ignore rate limit headers
- Retry immediately on 429
- Make unnecessary API calls
- Use polling without delays

### 3. Error Handling

✅ **Do:**
- Check HTTP status codes
- Parse error messages
- Log errors with request IDs
- Implement retry logic for transient errors

❌ **Don't:**
- Assume all requests succeed
- Ignore error responses
- Retry on 4xx errors (except 429)
- Hide errors from monitoring

### 4. HTTPS

✅ **Do:**
- Always use HTTPS in production
- Verify SSL certificates
- Use TLS 1.2 or higher

❌ **Don't:**
- Use HTTP for sensitive data
- Disable certificate verification
- Ignore SSL warnings

### 5. Monitoring

✅ **Do:**
- Monitor rate limit usage
- Track authentication failures
- Alert on high error rates
- Log security events

❌ **Don't:**
- Log full API keys
- Ignore security warnings
- Skip regular audits

---

## Troubleshooting

### Authentication Issues

**Problem**: Getting 401 Unauthorized

**Solutions:**
1. Verify API key is set:
   ```bash
   echo $API_KEYS
   ```

2. Check header format:
   ```bash
   curl -H "X-API-Key: your_key" ...
   # NOT: "X-Api-Key" or "API-Key"
   ```

3. Verify key is valid:
   ```bash
   python scripts/manage_api_keys.py list --show-full
   ```

4. Check if auth is enabled:
   ```bash
   echo $AUTH_ENABLED
   # Should be "true"
   ```

### Rate Limiting Issues

**Problem**: Getting 429 Too Many Requests

**Solutions:**
1. Check rate limit headers:
   ```bash
   curl -I https://api.pokewatch.com/health
   # Look for X-RateLimit-* headers
   ```

2. Wait for reset:
   ```bash
   # Check X-RateLimit-Reset header
   # Wait until that timestamp
   ```

3. Use multiple API keys:
   ```python
   # Distribute load across keys
   keys = ['pk_key1', 'pk_key2', 'pk_key3']
   current_key = keys[request_count % len(keys)]
   ```

4. Implement caching:
   ```python
   # Cache responses to reduce API calls
   import requests_cache
   requests_cache.install_cache('pokewatch_cache', expire_after=300)
   ```

### CORS Issues

**Problem**: CORS errors in browser

**Solutions:**
1. Check allowed origins:
   ```bash
   echo $ALLOWED_ORIGINS
   ```

2. Verify origin matches exactly:
   ```
   Allowed: https://app.example.com
   Request: https://app.example.com  ✅
   Request: http://app.example.com   ❌ (http vs https)
   Request: https://app.example.com:3000  ❌ (includes port)
   ```

3. Use wildcard for development:
   ```bash
   ALLOWED_ORIGINS=*
   ```

4. Check preflight response:
   ```bash
   curl -X OPTIONS https://api.pokewatch.com/fair_price \
     -H "Origin: https://app.example.com" \
     -H "Access-Control-Request-Method: POST"
   ```

### Performance Issues

**Problem**: Slow API responses

**Solutions:**
1. Check response time header:
   ```bash
   curl -I https://api.pokewatch.com/health
   # Look for X-Response-Time
   ```

2. Use batch endpoints:
   ```python
   # Instead of multiple requests:
   for card_id in cards:
       get_prediction(card_id)

   # Use batch:
   get_batch_predictions(cards)
   ```

3. Enable caching (Day 4):
   ```bash
   CACHE_ENABLED=true
   REDIS_URL=redis://localhost:6379
   ```

### Debugging

**Enable debug logging:**

```bash
export LOG_LEVEL=DEBUG
uvicorn src.pokewatch.api.main:app --reload
```

**Check logs:**

```bash
tail -f logs/logs.txt
```

**Test authentication:**

```bash
# Test with valid key
curl -H "X-API-Key: pk_test_key" http://localhost:8000/health

# Test without key
curl http://localhost:8000/health

# Test with invalid key
curl -H "X-API-Key: invalid" http://localhost:8000/health
```

---

## Security Checklist

### Before Production

- [ ] Generate production API keys
- [ ] Store keys securely (environment variables, secret manager)
- [ ] Enable HTTPS
- [ ] Configure appropriate rate limits
- [ ] Whitelist specific CORS origins (no wildcards)
- [ ] Enable request logging
- [ ] Set up monitoring and alerts
- [ ] Review security headers
- [ ] Test authentication flow
- [ ] Test rate limiting
- [ ] Document API keys for team
- [ ] Set up key rotation schedule

### Regular Maintenance

- [ ] Rotate API keys (every 90 days)
- [ ] Review access logs for suspicious activity
- [ ] Update rate limits based on usage
- [ ] Audit active API keys
- [ ] Check for security updates
- [ ] Review and update CORS origins
- [ ] Test disaster recovery procedures

---

## Support

For security issues:
1. Check this guide
2. Review logs with request ID
3. Test with curl/Postman
4. Check environment variables
5. Verify configuration files

For security vulnerabilities, please report privately to the development team.

---

**Last Updated:** Week 2, Day 3 - Phase 3 Implementation
