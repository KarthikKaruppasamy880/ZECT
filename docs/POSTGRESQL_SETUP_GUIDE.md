# ZECT — PostgreSQL Setup Guide

Complete guide to setting up PostgreSQL for ZECT on Windows (local development) and Linux (production).

---

## Why PostgreSQL?

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Concurrency | Single writer | Multi-user, multi-connection |
| Scalability | Single file, ~1GB practical | Terabytes, millions of rows |
| Data Integrity | Basic | ACID, advanced constraints |
| Production Ready | Development only | Enterprise-grade |
| Backup/Restore | File copy | pg_dump, PITR, streaming replication |
| JSON Support | Limited | Full JSONB with indexing |

ZECT supports **both** via SQLAlchemy ORM — switch by changing one environment variable.

---

## Windows Local Setup

### Step 1: Install PostgreSQL

1. Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Choose **PostgreSQL 16** for Windows x86-64
3. Run installer with these settings:
   - Installation directory: Default (`C:\Program Files\PostgreSQL\16`)
   - Data directory: Default
   - **Password**: Set a strong superuser password (remember this!)
   - Port: **5432** (default)
   - Locale: Default
4. Check **pgAdmin 4** in Stack Builder (optional GUI tool)

### Step 2: Verify Installation

Open **Command Prompt** or **PowerShell**:
```cmd
"C:\Program Files\PostgreSQL\16\bin\psql" --version
```

Or add PostgreSQL to your PATH:
```cmd
setx PATH "%PATH%;C:\Program Files\PostgreSQL\16\bin"
```

Then restart your terminal and verify:
```cmd
psql --version
```

### Step 3: Create the ZECT Database

**Option A: Using psql (Command Line)**
```cmd
psql -U postgres
```
Enter your superuser password, then run:
```sql
CREATE DATABASE zect_db;
CREATE USER zect_user WITH PASSWORD 'ZectSecure2026!';
GRANT ALL PRIVILEGES ON DATABASE zect_db TO zect_user;
ALTER DATABASE zect_db OWNER TO zect_user;
\q
```

**Option B: Using pgAdmin (GUI)**
1. Open pgAdmin 4 from Start Menu
2. Connect to local server (enter your superuser password)
3. Right-click **Databases** → Create → Database
4. Name: `zect_db`, Owner: `postgres` → Save
5. Right-click **Login/Group Roles** → Create → Login/Group Role
6. Name: `zect_user`, Password tab: `ZectSecure2026!`, Privileges tab: Can login = Yes → Save

### Step 4: Configure ZECT Backend

Edit `backend/.env`:
```env
DATABASE_URL=postgresql://zect_user:ZectSecure2026!@localhost:5432/zect_db
```

Or if using the `postgres` superuser directly:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/zect_db
```

### Step 5: Install Python PostgreSQL Driver

```cmd
cd backend
poetry install
```

The `psycopg[binary]` driver is already in `pyproject.toml` — no extra install needed.

### Step 6: Start the Backend

```cmd
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On first start, the app will:
1. Connect to PostgreSQL
2. Create all tables (projects, repos, settings, token_logs)
3. Seed demo data (6 projects, 2 repos, 10 settings)

### Step 7: Verify Database

Open psql or pgAdmin and check:
```sql
\c zect_db
\dt
SELECT COUNT(*) FROM projects;
SELECT COUNT(*) FROM repos;
SELECT COUNT(*) FROM settings;
SELECT COUNT(*) FROM token_logs;
```

Expected output:
- projects: 6 rows
- repos: 2 rows
- settings: 10 rows
- token_logs: 0 rows (fills up as you use AI features)

---

## Linux Setup (Ubuntu/Debian)

```bash
# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << 'EOF'
CREATE DATABASE zect_db;
CREATE USER zect_user WITH PASSWORD 'ZectSecure2026!';
GRANT ALL PRIVILEGES ON DATABASE zect_db TO zect_user;
ALTER DATABASE zect_db OWNER TO zect_user;
EOF

# Verify
sudo -u postgres psql -c "\l" | grep zect
```

Update `backend/.env`:
```env
DATABASE_URL=postgresql://zect_user:ZectSecure2026!@localhost:5432/zect_db
```

---

## Switching from SQLite to PostgreSQL

If you have an existing SQLite database with data you want to keep:

### Export from SQLite
```bash
cd backend
python -c "
from app.database import engine, SessionLocal
from app.models import Project, Repo, Setting, TokenLog
from sqlalchemy.orm import Session
import json

db = SessionLocal()
data = {
    'projects': [{'name': p.name, 'team': p.team, 'status': p.status, 'current_stage': p.current_stage, 'completion_percent': p.completion_percent} for p in db.query(Project).all()],
    'repos': [{'owner': r.owner, 'repo_name': r.repo_name, 'project_id': r.project_id} for r in db.query(Repo).all()],
    'settings': [{'key': s.key, 'value': s.value, 'setting_type': s.setting_type, 'label': s.label} for s in db.query(Setting).all()],
}
with open('backup.json', 'w') as f:
    json.dump(data, f, indent=2)
print(f'Exported: {len(data[\"projects\"])} projects, {len(data[\"repos\"])} repos, {len(data[\"settings\"])} settings')
"
```

### Switch DATABASE_URL and Restart
The app will auto-create tables and seed fresh demo data. For existing data, you can import the backup.json manually.

---

## Connection String Reference

```
postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE

Examples:
  Local:      postgresql://postgres:mypass@localhost:5432/zect_db
  RDS:        postgresql://zect_admin:pass@mydb.abc123.us-east-1.rds.amazonaws.com:5432/zect_db
  Supabase:   postgresql://postgres:pass@db.abcdef.supabase.co:5432/postgres
  Neon:       postgresql://user:pass@ep-cool-name.us-east-2.aws.neon.tech/zect_db
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `FATAL: password authentication failed` | Check password in DATABASE_URL matches what you set |
| `could not connect to server: Connection refused` | PostgreSQL service not running: `net start postgresql-x64-16` (Windows) |
| `database "zect_db" does not exist` | Create it: `CREATE DATABASE zect_db;` |
| `role "zect_user" does not exist` | Create it: `CREATE USER zect_user WITH PASSWORD '...';` |
| `permission denied for schema public` | Run: `GRANT ALL ON SCHEMA public TO zect_user;` (PostgreSQL 15+) |

### Windows Service Commands
```cmd
# Check if PostgreSQL is running
sc query postgresql-x64-16

# Start PostgreSQL service
net start postgresql-x64-16

# Stop PostgreSQL service
net stop postgresql-x64-16
```

---

## Security Best Practices

1. **Never use `postgres` superuser in production** — always create a dedicated user
2. **Use strong passwords** — minimum 16 characters with mixed case, numbers, symbols
3. **Restrict network access** — only allow connections from your app server
4. **Enable SSL** — for any non-localhost connections
5. **Regular backups** — use `pg_dump` or RDS automated backups
6. **Keep PostgreSQL updated** — security patches are critical
