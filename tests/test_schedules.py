from datetime import date, timedelta


def test_schedule_overlap_on_create_and_update(client, factory, auth_headers):
    factory.create_admin()
    professional = factory.create_professional()
    headers = auth_headers("admin@test.com", "admin123")
    future = (date.today() + timedelta(days=5)).isoformat()

    first = client.post(
        "/schedules",
        headers=headers,
        json={
            "professionalId": professional["id"],
            "specialty": "Clínico Geral",
            "date": future,
            "startTime": "09:00",
            "endTime": "10:00",
            "status": "available",
        },
    )
    assert first.status_code == 201, first.text

    overlap = client.post(
        "/schedules",
        headers=headers,
        json={
            "professionalId": professional["id"],
            "specialty": "Clínico Geral",
            "date": future,
            "startTime": "09:30",
            "endTime": "10:30",
            "status": "available",
        },
    )
    assert overlap.status_code == 409

    second = client.post(
        "/schedules",
        headers=headers,
        json={
            "professionalId": professional["id"],
            "date": future,
            "startTime": "10:00",
            "endTime": "11:00",
            "status": "available",
        },
    )
    assert second.status_code == 201, second.text

    update_overlap = client.put(
        f"/schedules/{second.json()['id']}",
        headers=headers,
        json={"startTime": "09:45", "endTime": "10:45"},
    )
    assert update_overlap.status_code == 409

    filtered = client.get(
        f"/schedules?specialty=Clínico%20Geral&date={future}&status=available",
        headers=headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 2
