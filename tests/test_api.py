import io


def _png_bytes() -> bytes:
    # Minimal valid 1x1 PNG.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "3df40000000c4944415478da6360000002000155007acf1c9a0000000049454e44ae426082"
    )


def test_get_users_empty(client):
    resp = client.get("/users")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_user_success(client):
    resp = client.post(
        "/user",
        data={"name": "Test User", "email": "test-user@prima.it"},
        files={"avatar": ("test-avatar.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Test User"
    assert body["email"] == "test-user@prima.it"
    assert body["avatar_url"].endswith(".png")
    assert "prima-tech-challenge" in body["avatar_url"]


def test_created_user_appears_in_list(client):
    client.post(
        "/user",
        data={"name": "Test User", "email": "test-user@prima.it"},
        files={"avatar": ("avatar.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    resp = client.get("/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) == 1
    assert users[0]["email"] == "test-user@prima.it"


def test_duplicate_email_rejected(client):
    payload = {
        "data": {"name": "Test User", "email": "dupe@prima.it"},
        "files": {"avatar": ("a.png", io.BytesIO(_png_bytes()), "image/png")},
    }
    first = client.post("/user", **payload)
    assert first.status_code == 201

    second = client.post(
        "/user",
        data={"name": "Test User", "email": "dupe@prima.it"},
        files={"avatar": ("a.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert second.status_code == 409


def test_invalid_email_rejected(client):
    resp = client.post(
        "/user",
        data={"name": "Test User", "email": "not-an-email"},
        files={"avatar": ("a.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert resp.status_code == 422


def test_unsupported_content_type_rejected(client):
    resp = client.post(
        "/user",
        data={"name": "Test User", "email": "test2@prima.it"},
        files={"avatar": ("a.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert resp.status_code == 415


def test_empty_avatar_rejected(client):
    resp = client.post(
        "/user",
        data={"name": "Test User", "email": "test3@prima.it"},
        files={"avatar": ("a.png", io.BytesIO(b""), "image/png")},
    )
    assert resp.status_code == 400


def test_missing_fields_rejected(client):
    resp = client.post("/user", data={"name": "No Email"})
    assert resp.status_code == 422


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz_ok_when_db_reachable(client):
    resp = client.get("/readyz")
    assert resp.status_code == 200
