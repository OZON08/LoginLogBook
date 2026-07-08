def test_admin_page_returns_html(client):
    res = client.get("/admin")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "LoginLogBook Admin" in res.text
