PASSWORD = "correct horse battery"


def login(client, email="admin@example.com", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def login_csrf(client, email="admin@example.com"):
    """Sign in and return headers carrying the CSRF token."""
    return {"X-CSRF-Token": login(client, email).json()["csrf_token"]}
