# Security and threat considerations

## Design choices

- No arbitrary remote shell. Jobs describe validated tool operations; the agent rebuilds winget commands from the local catalog.
- Published environment revisions are immutable in PostgreSQL.
- Pairing codes are hashed, expire in five minutes, and are single-use.
- Device credentials can be revoked. Replacing a device revokes the previous active device.
- Secrets live in `.env` (gitignored) or a production secret store. Logs redact common secret patterns.
- Security response headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`.
- CORS is limited to `FRONTEND_ORIGIN` with credentials.

## Threat notes

| Threat | Mitigation | Residual risk |
|---|---|---|
| Stolen refresh cookie | HttpOnly, path-scoped, CSRF on refresh, reuse revocation | XSS in the SPA can still call APIs while the session is live |
| Pairing code interception | Short TTL, hashed at rest, single-use, rate limit | Shoulder-surfing during the five-minute window |
| Malicious install payload from API | Agent ignores remote URL/hash/shell; local catalog pin required | Compromised local catalog file on the student machine |
| Instructor privilege before approval | `instructor_status` checked on every instructor route | Mis-approved instructors inherit full course powers |
| Auth brute force | In-process rate limit | Limit is per process; multi-task ECS needs a shared limiter |
| Install on developer PC during tests | Agent test mode; documented VM requirement | Operator can still approve a plan on a real machine |

## Production secrets

Do not commit production values. Inject `APP_SECRET_KEY`, database credentials, and Google OAuth secrets through the deployment secret store. Set `COOKIE_SECURE=true` behind HTTPS.
