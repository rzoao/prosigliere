"""
Test suite for Blog API
Using pytest and FastAPI TestClient
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, get_db, Base
import json

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def test_db():
    """Create and clean up test database for each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_get_empty_posts(client, test_db):
    response = client.get("/api/posts")
    assert response.status_code == 200
    assert response.json() == []


def test_get_posts_with_data(client, test_db):
    """Test getting posts when data exists."""
    # Create a post first
    post_data = {"title": "Test Post", "content": "Test content"}
    client.post("/api/posts", json=post_data)
    
    response = client.get("/api/posts")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Post"
    assert data[0]["comment_count"] == 0
    assert "created_at" in data[0]


def test_create_post(client, test_db):
    post_data = {
        "title": "Test Post",
        "content": "This is a test post content."
    }
    
    response = client.post("/api/posts", json=post_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["title"] == post_data["title"]
    assert data["content"] == post_data["content"]
    assert data["id"] == 1
    assert "created_at" in data
    assert "updated_at" in data
    assert data["comments"] == []
