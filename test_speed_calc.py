import time
from fastapi.testclient import TestClient
from main import app
from database import db_manager, TABLE_BIKE_DATA

client = TestClient(app)

def test_computed_speed_allows_insert(tmp_path):
    device_id = f"test-speed-{int(time.time())}"
    db_manager.init_tables()
    count_before = db_manager.execute_scalar(
        f"SELECT COUNT(*) FROM {TABLE_BIKE_DATA} WHERE device_id=?", (device_id,)
    ) or 0
    payload1 = {
        "latitude": 52.0,
        "longitude": 5.0,
        "speed": 0.0,
        "direction": 0.0,
        "device_id": device_id,
        "z_values": [0.1, 0.2],
    }
    client.post("/log", json=payload1)
    payload2 = {
        "latitude": 52.0005,
        "longitude": 5.0005,
        "speed": 0.0,
        "direction": 0.0,
        "device_id": device_id,
        "z_values": [0.1, 0.2],
    }
    resp = client.post("/log", json=payload2)
    assert resp.status_code == 200
    count_after = db_manager.execute_scalar(
        f"SELECT COUNT(*) FROM {TABLE_BIKE_DATA} WHERE device_id=?", (device_id,)
    )
    assert count_after > count_before
