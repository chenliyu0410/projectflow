def test_login_sets_http_only_session_cookie(client):
    response = client.post("/auth/login", json={
        "organization_key": "food",
        "username": "yu",
        "password": "demo-yu",
    })
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "user": {"id": body["user"]["id"], "username": "yu", "display_name": "游專案", "role": "admin"},
        "organization": {"id": body["organization"]["id"], "key": "food", "name": "毛研食品"},
    }
    cookie = response.headers["set-cookie"]
    assert "pf_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "demo-yu" not in response.text


def test_login_rejects_wrong_org_or_password(client):
    bad_org = client.post("/auth/login", json={"organization_key": "missing", "username": "yu", "password": "demo-yu"})
    bad_password = client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "wrong"})
    assert bad_org.status_code == 401
    assert bad_password.status_code == 401
    assert bad_org.json() == {"detail": "帳號或密碼錯誤"}
    assert bad_password.json() == {"detail": "帳號或密碼錯誤"}


def test_me_requires_valid_session_and_logout_revokes_it(client):
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "demo-yu"}).status_code == 200
    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_logout_revokes_only_current_session(client):
    first = client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "demo-yu"})
    first_cookie = first.cookies.get("pf_session")
    second = client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "demo-yu"})
    assert second.status_code == 200
    second_cookie = second.cookies.get("pf_session")
    assert first_cookie != second_cookie

    client.cookies.set("pf_session", first_cookie)
    assert client.post("/auth/logout").status_code == 204

    client.cookies.set("pf_session", second_cookie)
    assert client.get("/auth/me").status_code == 200


def test_user_cannot_forge_organization_in_me_payload(client):
    assert client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "demo-yu"}).status_code == 200
    response = client.get("/auth/me?organization_key=electronics")
    assert response.status_code == 200
    assert response.json()["organization"]["key"] == "food"
