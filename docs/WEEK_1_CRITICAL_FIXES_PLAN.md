# Week 1: Critical Fixes Implementation Plan

**Status:** Ready for approval  
**Timeline:** 4 weeks (4 critical fixes)  
**Effort:** 4 engineers × 10 days = 40 engineer-days

---

## FIX #1: XOR Encryption → Fernet (Days 1-3)

### Current State
**File:** `backend/app/security/secrets.py` (estimated location)

```python
# ❌ CURRENT (BROKEN)
class SecretsManager:
    def __init__(self):
        self.key = "zect-default-encrypt-key-change-me"
    
    def encrypt(self, plaintext):
        ciphertext = ""
        for i, char in enumerate(plaintext):
            key_char = self.key[i % len(self.key)]
            encrypted_char = chr(ord(char) ^ ord(key_char))
            ciphertext += encrypted_char
        return ciphertext
```

**Files to Modify:**
```
backend/app/
├── security/
│   ├── secrets.py           ← Replace XOR implementation
│   └── vault.py             ← NEW: AWS Secrets Manager integration
├── main.py                  ← Add vault initialization on startup
└── requirements.txt         ← Add: cryptography, boto3
```

### Fixed Implementation

**Step 1: Update `requirements.txt`**
```diff
+ cryptography==41.0.0      # For Fernet encryption
+ boto3==1.28.0             # For AWS Secrets Manager
```

**Step 2: Create `backend/app/security/vault.py` (NEW)**
```python
import boto3
from cryptography.fernet import Fernet
import os

class VaultManager:
    """Secure key management using AWS Secrets Manager"""
    
    def __init__(self):
        if os.getenv("ENV") == "production":
            self.client = boto3.client("secretsmanager")
            self.key = self._get_key_from_vault()
        else:
            # Dev: key from environment variable
            self.key = os.getenv("ENCRYPTION_KEY")
            if not self.key:
                raise ValueError("ENCRYPTION_KEY not set in .env")
    
    def _get_key_from_vault(self) -> bytes:
        """Fetch encryption key from AWS Secrets Manager"""
        try:
            response = self.client.get_secret_value(
                SecretId="zect/encryption-key"
            )
            return response["SecretString"].encode()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch encryption key: {e}")

# Global instance
vault = VaultManager()
```

**Step 3: Rewrite `backend/app/security/secrets.py`**
```python
from cryptography.fernet import Fernet
from app.security.vault import vault

class SecretsManager:
    """Secure encryption using Fernet (AES-128)"""
    
    def __init__(self):
        self.cipher = Fernet(vault.key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext to string"""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext to plaintext"""
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Global instance
secrets_manager = SecretsManager()
```

**Step 4: Update `backend/app/main.py`**
```python
# At startup
from app.security.vault import vault
from app.security.secrets import secrets_manager

@app.on_event("startup")
async def startup():
    # Initialize vault (will raise error if key not accessible)
    vault  # This triggers initialization
    secrets_manager  # This triggers cipher setup
    logger.info("✅ Encryption initialized (Fernet, AES-128)")
```

### Migration: Re-encrypt Existing Secrets

**Database Migration Script:**
```python
# scripts/migrate_encryption.py
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Secret
from app.security.secrets import secrets_manager
import sys

def migrate_secrets():
    """Migrate from XOR to Fernet encryption"""
    db = SessionLocal()
    
    # Get all secrets
    secrets = db.query(Secret).all()
    print(f"Found {len(secrets)} secrets to migrate")
    
    migrated = 0
    failed = 0
    
    for secret in secrets:
        try:
            # Decrypt with OLD method (XOR)
            # ⚠️ Need OLD XOR implementation temporarily
            old_plaintext = decrypt_xor(secret.value)
            
            # Re-encrypt with NEW method (Fernet)
            new_ciphertext = secrets_manager.encrypt(old_plaintext)
            
            # Update database
            secret.value = new_ciphertext
            db.commit()
            migrated += 1
        except Exception as e:
            print(f"❌ Failed to migrate secret {secret.id}: {e}")
            failed += 1
            db.rollback()
    
    print(f"✅ Migrated: {migrated}, Failed: {failed}")
    return failed == 0

if __name__ == "__main__":
    success = migrate_secrets()
    sys.exit(0 if success else 1)
```

**Steps to Execute:**
```bash
# 1. Install new dependencies
pip install -r requirements.txt

# 2. Generate new encryption key (ONE TIME)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output: b'XXXXXXX...' (save this)

# 3. Store key in AWS Secrets Manager
aws secretsmanager create-secret \
  --name zect/encryption-key \
  --secret-string "b'XXXXXXX...'"

# 4. Or in dev (.env)
echo "ENCRYPTION_KEY=b'XXXXXXX...'" >> .env

# 5. Run migration
python scripts/migrate_encryption.py

# 6. Verify: Try decrypting a secret
python -c "
from app.security.secrets import secrets_manager
ciphertext = '...'  # from database
plaintext = secrets_manager.decrypt(ciphertext)
print(plaintext)
"
```

### Testing

```python
# tests/test_encryption.py
def test_fernet_encryption():
    from app.security.secrets import secrets_manager
    
    # Test 1: Round-trip
    original = "openai_sk_secret123"
    encrypted = secrets_manager.encrypt(original)
    decrypted = secrets_manager.decrypt(encrypted)
    assert decrypted == original
    
    # Test 2: Non-deterministic
    encrypted1 = secrets_manager.encrypt(original)
    encrypted2 = secrets_manager.encrypt(original)
    assert encrypted1 != encrypted2  # Different each time!
    
    # Test 3: Tampering detection
    tampered = encrypted[:-5] + "XXXXX"
    try:
        secrets_manager.decrypt(tampered)
        assert False, "Should have raised error"
    except:
        pass  # Expected
```

### Success Criteria
- ✅ All secrets re-encrypted
- ✅ Tests pass (round-trip, non-determinism, tamper detection)
- ✅ No secrets accessible without key
- ✅ Key stored in vault, not in code

---

## FIX #2: CORS Misconfiguration (Day 4)

### Current State
**File:** `backend/app/main.py`

```python
# ❌ CURRENT (VULNERABLE)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # ALLOWS ANYONE!
    allow_credentials=True,     # DANGEROUS!
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Fixed Implementation

**Step 1: Update `backend/app/main.py`**
```python
from fastapi.middleware.cors import CORSMiddleware
import os

# Read allowed origins from environment
ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"  # Dev defaults
).split(",")

if os.getenv("ENV") == "production":
    ALLOWED_ORIGINS = [
        "https://yourdomain.com",
        "https://app.yourdomain.com",
        "https://mentrix.yourdomain.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,      # ✅ WHITELIST ONLY
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # ✅ NO WILDCARD
    allow_headers=["Content-Type", "Authorization"],  # ✅ EXPLICIT
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

**Step 2: Update `.env`**
```bash
# Development
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173

# Production (set on deployment)
# CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Testing

```python
# tests/test_cors.py
def test_cors_origin_whitelist(client):
    # ✅ Allowed origin
    response = client.get(
        "/api/projects",
        headers={"Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    
    # ❌ Disallowed origin
    response = client.get(
        "/api/projects",
        headers={"Origin": "https://attacker.com"}
    )
    assert "access-control-allow-origin" not in response.headers
```

### Success Criteria
- ✅ Only whitelisted origins can access API
- ✅ No `*` in CORS policy
- ✅ Security headers set
- ✅ Tests verify both allowed and blocked origins

---

## FIX #3: RBAC Enforcement (Days 5-9)

### Current State
**Files affected:**
```
backend/app/
├── routers/
│   ├── secrets_manager.py   ← NO role checks
│   ├── permissions.py       ← NO role checks
│   └── auth.py              ← Some checks, incomplete
├── core/
│   └── auth.py              ← Add decorators here
└── main.py                  ← Register decorators
```

### Fixed Implementation

**Step 1: Create `backend/app/core/auth.py` (NEW)**
```python
from functools import wraps
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models import User
from app.database import get_db

class PermissionDenied(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )

def require_role(*roles: str):
    """Decorator to enforce role-based access"""
    def decorator(func):
        async def wrapper(
            *args,
            current_user: User = Depends(get_current_user),
            **kwargs
        ):
            if current_user.role not in roles:
                raise PermissionDenied(
                    f"Requires one of: {', '.join(roles)}. "
                    f"Your role: {current_user.role}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_authentication():
    """Decorator to require valid JWT token"""
    def decorator(func):
        async def wrapper(
            *args,
            current_user: User = Depends(get_current_user),
            **kwargs
        ):
            if not current_user:
                raise PermissionDenied("Authentication required")
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def require_resource_access(resource_type: str):
    """Decorator to check resource-level permissions"""
    def decorator(func):
        async def wrapper(
            *args,
            current_user: User = Depends(get_current_user),
            db: Session = Depends(get_db),
            **kwargs
        ):
            # Extract resource_id from kwargs
            resource_id = kwargs.get(f"{resource_type}_id")
            
            # Check ownership/access
            has_access = can_user_access(
                current_user, resource_type, resource_id, db
            )
            
            if not has_access:
                raise PermissionDenied(
                    f"Access denied to {resource_type} {resource_id}"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

def can_user_access(
    user: User,
    resource_type: str,
    resource_id: int,
    db: Session
) -> bool:
    """Check if user has access to a specific resource"""
    
    if user.role == "admin":
        return True  # Admins access everything
    
    if resource_type == "secret":
        secret = db.query(Secret).get(resource_id)
        if not secret:
            return False
        
        # User can access secrets in their project
        return secret.project.team == user.team
    
    if resource_type == "project":
        project = db.query(Project).get(resource_id)
        if not project:
            return False
        
        # User can access projects in their team
        return project.team == user.team
    
    return False
```

**Step 2: Update `backend/app/routers/secrets_manager.py`**
```python
from fastapi import APIRouter, Depends
from app.core.auth import require_role, require_resource_access

router = APIRouter()

@router.get("/api/secrets")
@require_authentication()  # Any authenticated user
async def list_secrets(current_user: User, db: Session):
    # Only show secrets for user's team
    return db.query(Secret).filter(
        Secret.project.team == current_user.team
    ).all()

@router.delete("/api/secrets/{secret_id}")
@require_role("admin")  # ✅ ENFORCED!
async def delete_secret(
    secret_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    secret = db.query(Secret).get(secret_id)
    if not secret:
        raise HTTPException(status_code=404)
    
    # Extra check: is secret in user's scope?
    if not can_user_access(current_user, "secret", secret_id, db):
        raise PermissionDenied("Not your secret")
    
    db.delete(secret)
    db.commit()
    
    # ✅ LOG TO AUDIT TRAIL
    log_audit(current_user, "delete_secret", secret_id)
    
    return {"deleted": True}
```

**Step 3: Apply to All Sensitive Endpoints**

```python
# ✅ ADMIN ONLY
@require_role("admin")
async def create_user(...): ...

@require_role("admin")
async def delete_project(...): ...

@require_role("admin")
async def modify_permissions(...): ...

# ✅ LEAD ONLY
@require_role("admin", "lead")
async def approve_deployment(...): ...

# ✅ ANY AUTHENTICATED USER (with resource check)
@require_resource_access("project")
async def update_project(project_id: int, ...): ...
```

### Audit Logging Integration

```python
from app.models import AuditLog

def log_audit(user: User, action: str, resource_id: int, db: Session):
    """Log all sensitive actions"""
    audit = AuditLog(
        user_id=user.id,
        action=action,
        resource_id=resource_id,
        timestamp=datetime.utcnow()
    )
    db.add(audit)
    db.commit()
```

### Testing

```python
# tests/test_rbac.py
def test_admin_only_delete_secret(client):
    # Setup: Create user (developer role)
    developer = create_test_user(role="developer")
    secret = create_test_secret(id=1)
    
    # ❌ Developer cannot delete
    response = client.delete(
        "/api/secrets/1",
        headers={"Authorization": f"Bearer {developer.token}"}
    )
    assert response.status_code == 403
    assert "Requires admin" in response.json()["detail"]
    
    # ✅ Admin CAN delete
    admin = create_test_user(role="admin")
    response = client.delete(
        "/api/secrets/1",
        headers={"Authorization": f"Bearer {admin.token}"}
    )
    assert response.status_code == 200

def test_resource_level_access(client):
    # User A owns Project 1
    user_a = create_test_user(team="team_a")
    project_a = create_test_project(team="team_a", id=1)
    
    # User B in different team
    user_b = create_test_user(team="team_b")
    
    # ❌ User B cannot access Project 1
    response = client.get(
        "/api/projects/1",
        headers={"Authorization": f"Bearer {user_b.token}"}
    )
    assert response.status_code == 403
```

### Success Criteria
- ✅ 20+ sensitive endpoints have role checks
- ✅ All deletion endpoints require "admin" role
- ✅ All approval endpoints require "lead" or "admin"
- ✅ Resource-level access checks working
- ✅ Audit logs created for sensitive actions
- ✅ Tests verify access denial

---

## FIX #4: Rate Limiting (Per-User) (Days 10-13)

### Current State
```python
# ❌ CURRENT (TOO PERMISSIVE)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/ask")
@limiter.limit("6000/minute")  # 100 req/sec = easy DoS!
async def ask(request):
    ...
```

### Fixed Implementation

**Step 1: Update `requirements.txt`**
```diff
+ slowapi==0.1.9
+ redis==5.0.0  # For distributed rate limiting (optional)
```

**Step 2: Create `backend/app/core/rate_limit.py`**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from app.models import User
from app.database import SessionLocal

class UserBasedLimiter(Limiter):
    """Rate limit per user (not per IP)"""
    
    async def get_rate_limit_key(request: Request) -> str:
        """Extract user ID from JWT token"""
        try:
            token = request.headers.get("Authorization", "").split("Bearer ")[-1]
            if not token:
                return get_remote_address(request)  # Fallback to IP
            
            # Decode JWT and get user_id
            payload = decode_token(token)  # Your JWT decoder
            return f"user:{payload['user_id']}"
        except:
            return get_remote_address(request)  # Fallback to IP

limiter = UserBasedLimiter(key_func=get_rate_limit_key)
```

**Step 3: Update `backend/app/main.py`**
```python
from app.core.rate_limit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware to check token budget BEFORE rate limit
@app.middleware("http")
async def check_token_budget(request: Request, call_next):
    # Extract user from JWT
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[-1]
        payload = decode_token(token)
        user_id = payload.get("user_id")
        
        # Check budget
        db = SessionLocal()
        user = db.query(User).get(user_id)
        
        if user and user.tokens_used_today >= user.daily_token_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Daily token limit exceeded. "
                             f"Used: {user.tokens_used_today}, "
                             f"Limit: {user.daily_token_limit}"
                }
            )
        db.close()
    
    return await call_next(request)
```

**Step 4: Apply Rate Limits to AI Endpoints**
```python
@app.post("/api/ask")
@limiter.limit("60/minute")  # 1 per second per user
async def ask(request: AskRequest, current_user: User):
    estimated_tokens = estimate_tokens(request.prompt)
    
    # Check budget
    if current_user.tokens_used_today + estimated_tokens > current_user.daily_limit:
        raise BudgetExceeded(f"Would exceed daily limit")
    
    # Proceed
    response = await llm.ask(request)
    
    # Log tokens
    db.add(TokenLog(
        user_id=current_user.id,
        tokens_used=response.tokens,
        action="ask"
    ))
    db.commit()
    
    return response

@app.post("/api/build")
@limiter.limit("10/minute")  # More expensive operation
async def build(request: BuildRequest, current_user: User):
    estimated_tokens = estimate_tokens(request.code + request.context)
    
    if current_user.tokens_used_today + estimated_tokens > current_user.daily_limit:
        raise BudgetExceeded()
    
    return await llm.build(request)

@app.get("/api/projects")
@limiter.limit("100/minute")  # Cheap operation
async def list_projects(current_user: User):
    return db.query(Project).filter_by(team=current_user.team).all()
```

### Testing

```python
# tests/test_rate_limit.py
def test_rate_limit_per_user(client):
    user_a = create_test_user(id=1)
    user_b = create_test_user(id=2)
    
    # User A makes 60 requests in 1 minute (at limit)
    for i in range(60):
        response = client.post(
            "/api/ask",
            json={"prompt": f"question {i}"},
            headers={"Authorization": f"Bearer {user_a.token}"}
        )
        assert response.status_code == 200
    
    # User A 61st request (blocked)
    response = client.post(
        "/api/ask",
        json={"prompt": "question 61"},
        headers={"Authorization": f"Bearer {user_a.token}"}
    )
    assert response.status_code == 429
    
    # ✅ User B can still make requests (separate limit)
    response = client.post(
        "/api/ask",
        json={"prompt": "question"},
        headers={"Authorization": f"Bearer {user_b.token}"}
    )
    assert response.status_code == 200

def test_token_budget_enforcement(client):
    user = create_test_user(daily_limit=1000)
    user.tokens_used_today = 950
    
    # Request that would exceed budget
    response = client.post(
        "/api/build",
        json={"code": "...", "context": "..."},  # ~100 tokens
        headers={"Authorization": f"Bearer {user.token}"}
    )
    assert response.status_code == 429
    assert "Daily token limit exceeded" in response.json()["detail"]
```

### Success Criteria
- ✅ Rate limits per user, not per IP
- ✅ Different limits for cheap vs. expensive operations
- ✅ Token budget enforced before execution
- ✅ Clear error messages when limits exceeded
- ✅ Tests verify both per-user isolation and budget enforcement

---

## Week 1 Summary

| Fix | Days | Files | Tests | Status |
|-----|------|-------|-------|--------|
| XOR → Fernet | 1-3 | security/*, requirements.txt | ✅ 3 tests | Ready |
| CORS | 4 | main.py, .env | ✅ 2 tests | Ready |
| RBAC | 5-9 | core/auth.py, routers/* | ✅ 4 tests | Ready |
| Rate Limit | 10-13 | core/rate_limit.py, main.py | ✅ 2 tests | Ready |

**Total:** 13 days of focused security hardening

---

## Approval Checklist

Before I proceed with code changes, please confirm:

- [ ] **FIX #1 (XOR → Fernet)**: Proceed with implementation?
  - Will generate new encryption key
  - Will migrate all existing secrets
  - Will update 5 backend files

- [ ] **FIX #2 (CORS)**: Proceed with implementation?
  - Will restrict origins to whitelist
  - Will add security headers
  - Will update 2 files

- [ ] **FIX #3 (RBAC)**: Proceed with implementation?
  - Will add 20+ role checks
  - Will create decorators for easy application
  - Will add audit logging
  - Will update 10+ router files

- [ ] **FIX #4 (Rate Limiting)**: Proceed with implementation?
  - Will implement per-user limits
  - Will add token budget enforcement
  - Will create different limits per operation type

---

## Next Steps

1. **You approve** → I execute all changes in parallel
2. **Each fix tested** → Run test suite before committing
3. **Create PR** → Single PR with all 4 critical fixes
4. **Deploy to staging** → Verify in staging environment
5. **Monitor** → Watch for any issues before production

**Estimated Time to Complete:**
- Code: 2 engineer-days (parallel execution)
- Testing: 1 engineer-day
- Review: 1 engineer-day
- **Total: 4 days of work**

---

Ready to proceed? Confirm the checklist and I'll start implementing immediately.
