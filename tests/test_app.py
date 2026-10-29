def test_app_uses_testing_configuration(app):
    assert app.config["TESTING"] is True
    assert app.config["APP_ENV"] == "testing"
    assert app.config["APP_NAME"] == "WorkDesk"


def test_root_redirects_to_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_login_page_is_available(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "Iniciar sesión" in response.get_data(as_text=True)


def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


def test_unknown_route_returns_custom_404(client):
    response = client.get("/ruta-que-no-existe")

    content = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "Página no encontrada" in content


def test_health_check_reports_application_and_database_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {
        "application": "ok",
        "database": "ok",
        "status": "ok",
    }