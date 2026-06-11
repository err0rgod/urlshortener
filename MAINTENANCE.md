# Project Maintenance and Migration Guide

## Project Structure
- app.py: Main entry point and API routes.
- models.py: SQLModel database schemas.
- database.py: Database connection and CRUD operations.
- short_url_gen.py: ID generation (Sonyflake) and caching logic.
- validations.py: URL validation and Safe Browsing integration.
- templates/: HTML files for the frontend.

## Configuration (Environment Variables)
The application requires a .env file in the root directory with the following keys:
- DB_PATH: Connection string for PostgreSQL (e.g., postgresql://user:password@localhost/dbname).
- SAFE_BROWSING: Google Safe Browsing API Key.

## Database Configuration (PostgreSQL)
If migrating to a new database:
1. Create the database: CREATE DATABASE urlshortener;
2. Create the user: CREATE USER urluser WITH PASSWORD 'password';
3. Grant permissions: GRANT ALL PRIVILEGES ON DATABASE urlshortener TO urluser;
4. Ensure the schema exists. Run the following in the Python environment:
   python -c "from database import engine; from models import SQLModel; SQLModel.metadata.create_all(engine)"
5. If the table already exists, manually add the status column:
   ALTER TABLE urldata ADD COLUMN is_banned BOOLEAN DEFAULT FALSE;

## Process Management (Systemd)
The application is managed as a system service.
- Service File Location: /etc/systemd/system/urlshortener.service
- Reloading after code changes: sudo systemctl restart urlshortener
- Viewing logs: sudo journalctl -u urlshortener -f

## Reverse Proxy (Nginx)
The application is served via Nginx on port 80/443.
- Config Location: /etc/nginx/sites-available/urlshortener
- Critical header: proxy_set_header X-Forwarded-Proto $scheme; (Required for Cloudflare Full Strict mode).

## SSL and Cloudflare
- SSL is handled by Certbot on the server and Proxied by Cloudflare.
- Cloudflare SSL mode must be set to Full (Strict).
- Static IPv4 must be attached in the AWS Lightsail console.

## Update Workflow
To update the application with new code:
1. Pull the latest code (git pull or scp).
2. Activate the virtual environment: source venv/bin/activate
3. Install new dependencies: pip install -r requirements.txt
4. Restart the service: sudo systemctl restart urlshortener
5. Restart Nginx if config changed: sudo systemctl restart nginx

## Migration to New Server
1. Export the database: pg_dump urlshortener > backup.sql
2. Install dependencies on new server (Redis, Postgres, Nginx, Python).
3. Import the database: psql urlshortener < backup.sql
4. Copy the .env file.
5. Reconfigure Nginx and Systemd as per the paths above.
6. Update the A record in Cloudflare to the new server IP.
