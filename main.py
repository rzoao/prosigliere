from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import List
import uvicorn


# TODO: Move to environment variables for production
DATABASE_URL = "sqlite:///./blog.db"  # Using SQLite for simplicity
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    comments = relationship("Comment", back_populates="blog_post", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    blog_post_id = Column(Integer, ForeignKey("blog_posts.id"), nullable=False)
    blog_post = relationship("BlogPost", back_populates="comments")


class BlogPostSummary(BaseModel):
    id: int
    title: str
    comment_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


app = FastAPI(
    title="Blog API",
    description="RESTful API for managing blog posts and comments",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# API Endpoints
@app.get("/api/posts", response_model=List[BlogPostSummary])
async def get_all_posts(db: Session = Depends(get_db)):
    """
    Retrieve all blog posts with their comment counts.
    """
    # TODO: add pagination
    posts = db.query(BlogPost).all()
    
    result = []
    for post in posts:
        result.append(BlogPostSummary(
            id=post.id,
            title=post.title,
            comment_count=len(post.comments),
            created_at=post.created_at
        ))
    
    return result


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # TODO: Disable in production
        log_level="info"
    )
