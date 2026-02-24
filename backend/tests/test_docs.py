def test_docs_route_serves_swagger_ui(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.content_type
    body = response.get_data(as_text=True)
    assert "SwaggerUIBundle" in body
    assert "/openapi.yaml" in body


def test_openapi_route_serves_spec_file(client):
    response = client.get("/openapi.yaml")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "openapi: 3.1.0" in body
    assert "/api/auth/login:" in body
