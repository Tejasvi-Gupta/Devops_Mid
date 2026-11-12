# Authentication and authorization

## Sign-in

- Email and password (Argon2id). Password rule: at least 12 characters with one letter and one number.
- Google ID token verification is implemented. It returns HTTP 503 until `GOOGLE_CLIENT_ID` is set.
- Access token: JWT, about 15 minutes, stored in frontend memory.
- Refresh token: httpOnly cookie `epp_refresh`, path `/api/v1/auth`.
- CSRF cookie `epp_csrf` (readable by JS) must be sent as `X-CSRF-Token` on refresh.
- Refresh-token reuse revokes all sessions for that user.

## Registration rules

- Public registration may create `student` or `instructor` only.
- Instructor accounts start with `instructor_status=pending` and cannot manage courses until an administrator approves them.
- Rejected instructors are demoted to `student`.
- Administrators are never created through the public API.

## Authorization checks

| Surface | Guard |
|---|---|
| Instructor course and environment mutations | `role=instructor` and `instructor_status=approved`, plus ownership |
| Student jobs, devices, enrollments | Authenticated student and resource ownership |
| Admin approval, suspend, audit | `role=admin` |
| Agent work, detection, verification | Device bearer credential that is not a JWT shape |

Sensitive operations write audit log rows. Auth and pairing endpoints are rate limited in-process (10 auth attempts / 600s, 5 pairing attempts / 600s per key). Multi-instance production should replace the in-process limiter with a shared store.
