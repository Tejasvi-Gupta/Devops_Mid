# API overview

Base path: `/api/v1`. OpenAPI is available at `/docs` when the API is running locally.

## Auth

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | student or instructor |
| POST | `/auth/login` | sets refresh cookie |
| POST | `/auth/refresh` | requires CSRF header |
| POST | `/auth/logout` | |
| GET | `/auth/me` | current user |
| POST | `/auth/google` | 503 until Google client id is set |

## Platform

Courses, enrollments, environments, revisions, publish, jobs, devices, pairing codes, notifications, catalog, and student environment list live under `/api/v1` as implemented in `backend/app/api/v1/platform.py`.

## Agent

Unauthenticated pairing: `POST /devices/pair`. Authenticated device routes under `/agent/*` use the device bearer token.

## Admin

Instructor approve/reject, user suspend/reactivate, audit, and health: `backend/app/api/v1/admin.py`. Health: `GET /api/v1/health/live`, `GET /api/v1/health/ready`.
