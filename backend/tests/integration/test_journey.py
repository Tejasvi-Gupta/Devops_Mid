import uuid

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models import User
from fastapi.testclient import TestClient

REQUIREMENTS = [
    {"tool": "python", "version_constraint": "==3.12.10", "mandatory": True},
    {"tool": "git", "version_constraint": "==2.56.0.3", "mandatory": False},
]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def register(client, email, role="student", name="Test User"):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": "correct-horse-1", "requested_role": role},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["access_token"], body["user"]


def test_instructor_publish_student_setup_failure_and_revision(migrated_test_database):
    with TestClient(app) as client:
        db = SessionLocal()
        db.add(
            User(
                name="Platform Admin",
                email="admin@example.com",
                password_hash=hash_password("correct-horse-1"),
                role="admin",
                instructor_status="not_applicable",
            )
        )
        db.commit()
        db.close()
        admin_token, _admin = register_login(client, "admin@example.com")
        instructor_token, instructor = register(client, "inst@example.com", "instructor", "Instructor")
        assert instructor["instructor_status"] == "pending"
        blocked = client.post(
            "/api/v1/courses",
            headers=auth(instructor_token),
            json={"name": "CS 101", "description": "Intro", "class_code": "CS101-A"},
        )
        assert blocked.status_code == 403

        approved = client.post(
            f"/api/v1/admin/instructors/{instructor['id']}/approve",
            headers=auth(admin_token),
        )
        assert approved.status_code == 200
        instructor_token, _instructor = register_login(client, "inst@example.com")

        course = client.post(
            "/api/v1/courses",
            headers=auth(instructor_token),
            json={"name": "CS 101", "description": "Intro", "class_code": "CS101-A"},
        )
        assert course.status_code == 201, course.text
        course_id = course.json()["id"]
        environment = client.post(
            "/api/v1/environments",
            headers=auth(instructor_token),
            json={"course_id": course_id, "name": "Backend lab", "description": "", "requirements": REQUIREMENTS},
        )
        assert environment.status_code == 201, environment.text
        revision_id = environment.json()["revisions"][0]["id"]
        published = client.post(f"/api/v1/revisions/{revision_id}/publish", headers=auth(instructor_token))
        assert published.status_code == 200
        immutable = client.put(
            f"/api/v1/revisions/{revision_id}",
            headers=auth(instructor_token),
            json=REQUIREMENTS,
        )
        assert immutable.status_code == 409

        student_token, student = register(client, "student@example.com", "student", "Student")
        enrolled = client.post(
            f"/api/v1/courses/{course_id}/enrollments",
            headers=auth(instructor_token),
            json={"email": "student@example.com"},
        )
        assert enrolled.status_code == 201, enrolled.text
        other_token, _other = register(client, "other@example.com")
        hidden = client.get(f"/api/v1/courses/{course_id}", headers=auth(other_token))
        assert hidden.status_code == 403

        code = client.post("/api/v1/devices/pairing-codes", headers=auth(student_token), json={})
        assert code.status_code == 200, code.text
        pairing_code = code.json()["pairing_code"]
        paired = client.post(
            "/api/v1/devices/pair",
            json={"code": pairing_code, "display_name": "Lab laptop", "platform": "windows"},
        )
        assert paired.status_code == 201, paired.text
        device_token = paired.json()["device_credential"]
        reused = client.post(
            "/api/v1/devices/pair",
            json={"code": pairing_code, "display_name": "Again", "platform": "windows"},
        )
        assert reused.status_code == 401

        environment_id = environment.json()["id"]
        job = client.post(
            "/api/v1/jobs",
            headers=auth(student_token),
            json={"environment_id": environment_id, "idempotency_key": str(uuid.uuid4()), "operation": "provision"},
        )
        assert job.status_code == 201, job.text
        job_id = job.json()["id"]
        duplicate = client.post(
            "/api/v1/jobs",
            headers=auth(student_token),
            json={"environment_id": environment_id, "idempotency_key": str(uuid.uuid4()), "operation": "provision"},
        )
        assert duplicate.status_code == 409
        stranger = client.get(f"/api/v1/jobs/{job_id}", headers=auth(other_token))
        assert stranger.status_code == 403

        device_headers = {"Authorization": f"Bearer {device_token}"}
        detected = client.post(
            f"/api/v1/agent/jobs/{job_id}/detection",
            headers=device_headers,
            json={"tools": [{"tool": "python", "installed": False, "functional": False}, {"tool": "git", "installed": False, "functional": False}]},
        )
        assert detected.status_code == 200, detected.text
        assert detected.json()["status"] == "awaiting_approval"
        missing = client.post(f"/api/v1/jobs/{job_id}/approve", headers=auth(student_token), json={"acknowledgements": []})
        assert missing.status_code == 422
        approved = client.post(
            f"/api/v1/jobs/{job_id}/approve",
            headers=auth(student_token),
            json={"acknowledgements": ["elevation"]},
        )
        assert approved.status_code == 200
        started = client.post(f"/api/v1/agent/jobs/{job_id}/start", headers=device_headers)
        assert started.status_code == 200
        assert started.json()["status"] == "installing"
        failed = client.post(
            f"/api/v1/agent/jobs/{job_id}/verification",
            headers=device_headers,
            json={
                "tools": [{"tool": "python", "installed": False, "functional": False}],
                "install_failures": [{"tool": "python", "category": "installer_failed", "message": "winget returned an error"}],
            },
        )
        assert failed.status_code == 200, failed.text
        assert failed.json()["status"] == "failed"
        readiness = client.get(f"/api/v1/courses/{course_id}/readiness", headers=auth(instructor_token))
        assert readiness.status_code == 200
        assert "winget returned an error" in str(readiness.json())
        assert "Bearer" not in str(readiness.json())

        retried = client.post(
            f"/api/v1/jobs/{job_id}/retry?idempotency_key={uuid.uuid4()}",
            headers=auth(student_token),
        )
        assert retried.status_code == 201, retried.text
        retry_id = retried.json()["id"]
        compliant = client.post(
            f"/api/v1/agent/jobs/{retry_id}/detection",
            headers=device_headers,
            json={
                "tools": [
                    {"tool": "python", "installed": True, "version": "3.12.10", "functional": True},
                    {"tool": "git", "installed": True, "version": "2.56.0.3", "functional": True},
                ]
            },
        )
        assert compliant.status_code == 200, compliant.text
        assert compliant.json()["status"] == "verifying"
        verified = client.post(
            f"/api/v1/agent/jobs/{retry_id}/verification",
            headers=device_headers,
            json={
                "tools": [
                    {"tool": "python", "installed": True, "version": "3.12.10", "functional": True},
                    {"tool": "git", "installed": True, "version": "2.56.0.3", "functional": True},
                ]
            },
        )
        assert verified.status_code == 200, verified.text
        assert verified.json()["status"] == "completed"
        states = client.get("/api/v1/student/environments", headers=auth(student_token)).json()
        assert states[0]["status"] == "ready"

        nxt = client.post(f"/api/v1/environments/{environment_id}/revisions", headers=auth(instructor_token))
        assert nxt.status_code == 201, nxt.text
        updated = client.put(
            f"/api/v1/revisions/{nxt.json()['id']}",
            headers=auth(instructor_token),
            json=REQUIREMENTS + [{"tool": "node", "version_constraint": "==24.22.1", "mandatory": True}],
        )
        assert updated.status_code == 200, updated.text
        republished = client.post(f"/api/v1/revisions/{nxt.json()['id']}/publish", headers=auth(instructor_token))
        assert republished.status_code == 200, republished.text
        states = client.get("/api/v1/student/environments", headers=auth(student_token)).json()
        assert states[0]["status"] == "needs_update"
        notes = client.get("/api/v1/notifications", headers=auth(student_token)).json()
        assert any(item["type"] == "revision_published" for item in notes["items"])
        del student


def register_login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-1"})
    assert response.status_code == 200, response.text
    body = response.json()
    return body["access_token"], body["user"]
