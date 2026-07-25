def test_public_registration_login_and_permissions(client, factory, auth_headers):
    registration = client.post(
        "/patients/register",
        json={
            "name": "Maria da Silva",
            "cpf": "12345678900",
            "email": "maria@example.com",
            "password": "maria123",
            "birthDate": "1995-03-10",
            "phone": "83999999999",
            "priorityGroup": "nenhum",
        },
    )
    assert registration.status_code == 201, registration.text
    patient = registration.json()
    assert patient["role"] == "patient"
    assert patient["cpf"] == "12345678900"

    login = client.post(
        "/auth/login",
        json={"identifier": "123.456.789-00", "password": "maria123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == patient["id"]

    public_create_professional = client.post(
        "/users",
        json={
            "role": "professional",
            "name": "Tentativa",
            "email": "tentativa@example.com",
            "password": "tentativa123",
            "specialty": "Pediatria",
            "council": "CRM-X",
        },
    )
    assert public_create_professional.status_code == 401

    factory.create_admin()
    admin_headers = auth_headers("admin@test.com", "admin123")
    professional = client.post(
        "/users",
        headers=admin_headers,
        json={
            "role": "professional",
            "name": "Dra. Ana",
            "cpf": "11122233344",
            "email": "ana@example.com",
            "password": "ana12345",
            "phone": "83988888888",
            "specialty": "Pediatria",
            "council": "CRM-ANA-1",
        },
    )
    assert professional.status_code == 201, professional.text

    patient_headers = auth_headers("12345678900", "maria123")
    forbidden = client.get("/users?role=patient", headers=patient_headers)
    assert forbidden.status_code == 403

    public_professionals = client.get("/users?role=professional", headers=patient_headers)
    assert public_professionals.status_code == 200
    assert public_professionals.json()[0]["specialty"] == "Pediatria"
    assert public_professionals.json()[0].get("email") is None


def test_admin_crud_including_delete(client, factory, auth_headers):
    first_admin = factory.create_admin()
    headers = auth_headers("admin@test.com", "admin123")

    second = client.post(
        "/users",
        headers=headers,
        json={
            "role": "admin",
            "name": "Segundo Administrador",
            "email": "admin2@test.com",
            "password": "admin2123",
            "position": "Coordenador",
        },
    )
    assert second.status_code == 201, second.text
    second_id = second.json()["id"]

    updated = client.put(
        f"/users/{second_id}",
        headers=headers,
        json={"name": "Administrador Atualizado"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Administrador Atualizado"

    self_delete = client.delete(f"/users/{first_admin['id']}", headers=headers)
    assert self_delete.status_code == 409

    deleted = client.delete(f"/users/{second_id}", headers=headers)
    assert deleted.status_code == 204


def test_refresh_rotation_and_logout_revocation(client, factory):
    factory.create_admin()
    login = client.post(
        "/auth/login",
        json={"identifier": "admin@test.com", "password": "admin123"},
    )
    assert login.status_code == 200
    original = login.json()

    refreshed = client.post(
        "/auth/refresh",
        json={"refreshToken": original["refreshToken"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    rotated = refreshed.json()
    assert rotated["refreshToken"] != original["refreshToken"]

    reused = client.post(
        "/auth/refresh",
        json={"refreshToken": original["refreshToken"]},
    )
    assert reused.status_code == 401

    headers = {"Authorization": f"Bearer {rotated['accessToken']}"}
    logout = client.post(
        "/auth/logout",
        headers=headers,
        json={"refreshToken": rotated["refreshToken"]},
    )
    assert logout.status_code == 204

    revoked_access = client.get("/users?role=professional", headers=headers)
    assert revoked_access.status_code == 401
