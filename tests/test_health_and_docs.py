def test_health_and_openapi_are_available(client):
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}

    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/auth/login" in paths
    assert "/appointments" in paths
    assert "/waitlist" in paths
