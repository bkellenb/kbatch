import os
import pytest
import requests

from fastapi.testclient import TestClient

from .main import app
from rich.traceback import install
install(show_locals=True)


client = TestClient(app)

USERNAME = "taugspurger"


def authenticate_side_effect(token):
    if token == "abc":
        return dict(name=USERNAME, groups=[])


@pytest.fixture
def mock_hub(mocker):
    yield mocker.patch(
        "app.main.auth.user_for_token",
        autospec=True,
        side_effect=authenticate_side_effect,
    )


@pytest.fixture(scope="function", autouse=True)
async def db():
    from app.main import database
   
    await database.execute("DELETE FROM jobs")
    yield


@pytest.mark.usefixtures("mock_hub", "db")
class TestKBatch:
    def test_read_main(self):
        response = client.get("/")
        assert response.status_code == 200

        response = client.get("/services/kbatch/")
        assert response.status_code == 200


    def test_list_jobs_authenticated(self):
        response = client.get("/services/kbatch/jobs/")
        assert response.status_code == 404

        data = {"command": ["ls", "-lh"], "image": "alpine"}
        response = client.post(
            "/services/kbatch/jobs/",
            json=data,
        )
        assert response.status_code == 307
     

    def test_list_jobs(self):
        response = client.get(
            "/services/kbatch/jobs/", headers={"Authorization": "token abc"}
        )
        assert response.status_code == 200
        assert response.json() == []

        data = {"command": ["ls", "-lh"], "image": "alpine"}
        response = client.post(
            "/services/kbatch/jobs/",
            headers={"Authorization": "token abc"},
            json=data,
        )
        assert response.status_code == 200
        result = response.json()
        assert result.pop("id")
        assert result.pop("username") == USERNAME
        assert result.pop("name")
        assert result.pop("script") is None

        assert result == data

    def test_post_script(self):

        script = "ls -lh"

        response = client.get(
            "/services/kbatch/jobs/", headers={"Authorization": "token abc"}
        )
        assert response.status_code == 200
        assert response.json() == []

        data = {"script": script, "image": "alpine"}
        response = client.post(
            "/services/kbatch/jobs/",
            headers={"Authorization": "token abc"},
            json=data,
        )
        assert response.status_code == 200
        result = response.json()
        assert result.pop("id")
        assert result.pop("username") == USERNAME
        assert result.pop("name")
        assert result.pop("command") is None

        assert result == data