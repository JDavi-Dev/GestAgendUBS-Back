from datetime import date


def test_waitlist_priority_and_position(client, factory, auth_headers):
    factory.create_admin()
    high = factory.create_patient(
        cpf="55555555555",
        email="idoso@test.com",
        name="Paciente Idoso",
        birth_date=date(1950, 1, 1),
    )
    medium = factory.create_patient(
        cpf="66666666666",
        email="gestante@test.com",
        name="Paciente Gestante",
        birth_date=date(1995, 1, 1),
        priority_group="gestante",
    )
    low = factory.create_patient(
        cpf="77777777777",
        email="comum@test.com",
        name="Paciente Comum",
        birth_date=date(1995, 1, 1),
    )

    low_headers = auth_headers("77777777777", "patient123")
    medium_headers = auth_headers("66666666666", "patient123")
    high_headers = auth_headers("55555555555", "patient123")
    admin_headers = auth_headers("admin@test.com", "admin123")

    for headers in [low_headers, medium_headers, high_headers]:
        response = client.post(
            "/waitlist",
            headers=headers,
            json={"specialty": "Cardiologia", "patientId": low["id"]},
        )
        assert response.status_code == 201, response.text

    rows = client.get("/waitlist?specialty=Cardiologia", headers=admin_headers)
    assert rows.status_code == 200
    payload = rows.json()
    assert [row["priority"] for row in payload] == ["alta", "media", "baixa"]
    assert [row["position"] for row in payload] == [1, 2, 3]
    assert [row["patientId"] for row in payload] == [high["id"], medium["id"], low["id"]]

    low_view = client.get("/waitlist", headers=low_headers)
    assert low_view.status_code == 200
    assert low_view.json()[0]["position"] == 3


def test_dashboard_metrics_are_admin_only(client, factory, auth_headers):
    factory.create_admin()
    factory.create_patient(cpf="88888888888", email="patient@test.com")
    admin_headers = auth_headers("admin@test.com", "admin123")
    patient_headers = auth_headers("88888888888", "patient123")

    forbidden = client.get("/dashboard/metrics", headers=patient_headers)
    assert forbidden.status_code == 403

    metrics = client.get("/dashboard/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    assert metrics.json()["patients"] == 1
    assert metrics.json()["administrators"] == 1


def test_admin_can_allocate_waitlist_entry(client, factory, auth_headers):
    from datetime import timedelta

    factory.create_admin()
    professional = factory.create_professional(
        email="cardio@test.com", council="CRM-CARDIO", specialty="Cardiologia"
    )
    patient = factory.create_patient(cpf="90909090909", email="wait@test.com")
    admin_headers = auth_headers("admin@test.com", "admin123")
    patient_headers = auth_headers("90909090909", "patient123")

    joined = client.post(
        "/waitlist",
        headers=patient_headers,
        json={"specialty": "Cardiologia"},
    )
    assert joined.status_code == 201, joined.text

    schedule = client.post(
        "/schedules",
        headers=admin_headers,
        json={
            "professionalId": professional["id"],
            "date": (date.today() + timedelta(days=8)).isoformat(),
            "startTime": "08:00",
            "endTime": "09:00",
        },
    )
    assert schedule.status_code == 201, schedule.text

    allocated = client.post(
        f"/waitlist/{joined.json()['id']}/allocate",
        headers=admin_headers,
        json={"scheduleId": schedule.json()["id"]},
    )
    assert allocated.status_code == 200, allocated.text
    assert allocated.json()["status"] == "alocado"
    assert allocated.json()["allocatedAppointmentId"] is not None

    appointments = client.get(
        f"/appointments?patientId={patient['id']}",
        headers=admin_headers,
    )
    assert appointments.status_code == 200
    assert len(appointments.json()) == 1
