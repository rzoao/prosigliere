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


def test_get_post_by_id(client, test_db):
    post_data = {"title": "Specific Post", "content": "Specific content"}
    create_response = client.post("/api/posts", json=post_data)
    post_id = create_response.json()["id"]
    
    response = client.get(f"/api/posts/{post_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Specific Post"
    assert data["content"] == "Specific content"
    assert data["comments"] == []


def test_get_nonexistent_post(client, test_db):
    response = client.get("/api/posts/999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_create_comment(client, test_db):
    post_data = {"title": "Post for Comment", "content": "Content"}
    create_response = client.post("/api/posts", json=post_data)
    post_id = create_response.json()["id"]
    
    comment_data = {
        "content": "This is a test comment",
        "author": "Test Author"
    }
    
    response = client.post(f"/api/posts/{post_id}/comments", json=comment_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["content"] == comment_data["content"]
    assert data["author"] == comment_data["author"]
    assert "created_at" in data


def test_create_comment_on_nonexistent_post(client, test_db):
    comment_data = {"content": "Comment", "author": "Author"}
    
    response = client.post("/api/posts/999/comments", json=comment_data)
    assert response.status_code == 404


def test_comment_validation(client, test_db):
    post_data = {"title": "Post", "content": "Content"}
    create_response = client.post("/api/posts", json=post_data)
    post_id = create_response.json()["id"]
    
    response = client.post(f"/api/posts/{post_id}/comments", 
                          json={"content": "", "author": "Author"})
    assert response.status_code == 422
    
    response = client.post(f"/api/posts/{post_id}/comments", 
                          json={"content": "Content", "author": ""})
    assert response.status_code == 422


def test_post_with_comments_integration(client, test_db):
    post_data = {"title": "Integration Test", "content": "Integration content"}
    create_response = client.post("/api/posts", json=post_data)
    post_id = create_response.json()["id"]
    
    comments = [
        {"content": "First comment", "author": "Author 1"},
        {"content": "Second comment", "author": "Author 2"}
    ]
    
    for comment in comments:
        client.post(f"/api/posts/{post_id}/comments", json=comment)
    
    response = client.get(f"/api/posts/{post_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["comments"]) == 2
    assert data["comments"][0]["content"] == "First comment"
    assert data["comments"][1]["content"] == "Second comment"
    
    posts_response = client.get("/api/posts")
    posts_data = posts_response.json()
    assert posts_data[0]["comment_count"] == 2
