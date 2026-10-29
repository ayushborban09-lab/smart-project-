import pytest
import uuid
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["offline_mode"] is True
    assert data["database"]["connected"] is True

def test_classroom_and_student_api(client):
    code = f"ROB-{uuid.uuid4().hex[:5].upper()}"
    # 1. Create class
    res = client.post("/api/classes", json={
        "name": "Robotics Engineering",
        "code": code,
        "subject": "Robotics",
        "department": "Engineering"
    })
    assert res.status_code == 201
    class_id = res.get_json()["class_id"]

    # 2. Get classes
    res2 = client.get("/api/classes")
    assert res2.status_code == 200
    classes = res2.get_json()["data"]
    assert any(c["id"] == class_id for c in classes)

    # 3. Add student
    res3 = client.post(f"/api/classes/{class_id}/students", json={
        "student_id_number": "ROB-001",
        "name": "Jordan Bell",
        "email": "jordan@university.edu"
    })
    assert res3.status_code == 201

def test_session_lifecycle_and_report_api(client):
    code = f"CS-{uuid.uuid4().hex[:5].upper()}"
    # Create class
    c_res = client.post("/api/classes", json={"name": "Data Structures", "code": code})
    assert c_res.status_code == 201
    cid = c_res.get_json()["class_id"]

    # Create session
    s_res = client.post("/api/sessions", json={
        "classroom_id": cid,
        "title": "Binary Trees & Graph Algorithms",
        "input_type": "synthetic"
    })
    assert s_res.status_code == 201
    sid = s_res.get_json()["session_id"]

    # Check status
    stat_res = client.get(f"/api/sessions/{sid}/status")
    assert stat_res.status_code == 200

    # Start session
    start_res = client.post(f"/api/sessions/{sid}/start", json={})
    assert start_res.status_code == 200

    # Stop session
    stop_res = client.post(f"/api/sessions/{sid}/stop", json={})
    assert stop_res.status_code == 200

    # Get report
    rep_res = client.get(f"/api/reports/{sid}")
    assert rep_res.status_code == 200
    rep_data = rep_res.get_json()["data"]
    assert rep_data["session"]["id"] == sid

    # Get HTML report
    html_res = client.get(f"/api/reports/{sid}/html")
    assert html_res.status_code == 200
    assert b"Multimodal Attendance & Engagement Agent Report" in html_res.data
