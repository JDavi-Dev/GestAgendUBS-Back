from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def create_schedule(client, headers, professional_id, target):
    response = client.post(
        "/schedules",
        headers=headers,
        json={
            "professionalId": professional_id,
            "date": target.date().isoformat(),
            "startTime": target.strftime("%H:%M"),
            "endTime": (target + timedelta(hours=1)).strftime("%H:%M"),
            "status": "available",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_patient_cannot_book_for_another_and_double_booking_is_blocked(
    client, factory, auth_headers
):
    factory.create_admin()
    professional = factory.create_professional()
    first_patient = factory.create_patient(cpf="11111111111", email="p1@test.com")
    second_patient = factory.create_patient(cpf="22222222222", email="p2@test.com")

    admin_headers = auth_headers("admin@test.com", "admin123")
    first_headers = auth_headers("11111111111", "patient123")
    second_headers = auth_headers("22222222222", "patient123")

    target = datetime.now(ZoneInfo("America/Fortaleza")) + timedelta(days=4)
    target = target.replace(hour=9, minute=0, second=0, microsecond=0)
    schedule = create_schedule(client, admin_headers, professional["id"], target)

    first_booking = client.post(
        "/appointments",
        headers=first_headers,
        json={"scheduleId": schedule["id"], "patientId": second_patient["id"]},
    )
    assert first_booking.status_code == 201, first_booking.text
    assert first_booking.json()["patientId"] == first_patient["id"]

    second_booking = client.post(
        "/appointments",
        headers=second_headers,
        json={"scheduleId": schedule["id"]},
    )
    assert second_booking.status_code == 409


def test_cancellation_rule_before_and_after_24_hours(client, factory, auth_headers):
    factory.create_admin()
    professional = factory.create_professional()
    patient = factory.create_patient(cpf="33333333333", email="p3@test.com")
    admin_headers = auth_headers("admin@test.com", "admin123")
    patient_headers = auth_headers("33333333333", "patient123")

    now = datetime.now(ZoneInfo("America/Fortaleza"))
    near_target = (now + timedelta(hours=12)).replace(second=0, microsecond=0)
    far_target = (now + timedelta(hours=72)).replace(second=0, microsecond=0)

    near_schedule = create_schedule(client, admin_headers, professional["id"], near_target)
    near_booking = client.post(
        "/appointments", headers=patient_headers, json={"scheduleId": near_schedule["id"]}
    )
    assert near_booking.status_code == 201, near_booking.text
    blocked = client.patch(
        f"/appointments/{near_booking.json()['id']}/cancel",
        headers=patient_headers,
    )
    assert blocked.status_code == 409

    far_schedule = create_schedule(client, admin_headers, professional["id"], far_target)
    far_booking = client.post(
        "/appointments", headers=patient_headers, json={"scheduleId": far_schedule["id"]}
    )
    assert far_booking.status_code == 201, far_booking.text
    cancelled = client.patch(
        f"/appointments/{far_booking.json()['id']}/cancel",
        headers=patient_headers,
        json={"reason": "Compromisso pessoal"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"


def test_professional_can_mark_done_or_missed(client, factory, auth_headers):
    factory.create_admin()
    professional = factory.create_professional()
    factory.create_patient(cpf="44444444444", email="p4@test.com")
    admin_headers = auth_headers("admin@test.com", "admin123")
    patient_headers = auth_headers("44444444444", "patient123")
    professional_headers = auth_headers("professional@test.com", "prof1234")

    target = datetime.now(ZoneInfo("America/Fortaleza")) + timedelta(days=3)
    target = target.replace(hour=15, minute=0, second=0, microsecond=0)
    schedule = create_schedule(client, admin_headers, professional["id"], target)
    booking = client.post(
        "/appointments", headers=patient_headers, json={"scheduleId": schedule["id"]}
    ).json()

    result = client.patch(
        f"/appointments/{booking['id']}/status",
        headers=professional_headers,
        json={"status": "done", "notes": "Atendimento realizado."},
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "done"


def test_patient_cannot_have_overlapping_appointments(client, factory, auth_headers):
    factory.create_admin()
    professional_one = factory.create_professional(
        email="p1prof@test.com", council="CRM-OVER-1", specialty="Clínico Geral"
    )
    professional_two = factory.create_professional(
        email="p2prof@test.com", council="CRM-OVER-2", specialty="Cardiologia"
    )
    factory.create_patient(cpf="12121212121", email="overlap-patient@test.com")

    admin_headers = auth_headers("admin@test.com", "admin123")
    patient_headers = auth_headers("12121212121", "patient123")
    target = datetime.now(ZoneInfo("America/Fortaleza")) + timedelta(days=6)
    target = target.replace(hour=10, minute=0, second=0, microsecond=0)

    first_schedule = create_schedule(client, admin_headers, professional_one["id"], target)
    second_schedule = create_schedule(client, admin_headers, professional_two["id"], target)

    first = client.post(
        "/appointments", headers=patient_headers, json={"scheduleId": first_schedule["id"]}
    )
    assert first.status_code == 201

    conflict = client.post(
        "/appointments", headers=patient_headers, json={"scheduleId": second_schedule["id"]}
    )
    assert conflict.status_code == 409
