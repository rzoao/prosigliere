from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
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


class CommentBase(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    author: str = Field(min_length=1, max_length=100)


class CommentCreate(CommentBase):
    pass


class CommentResponse(CommentBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BlogPostSummary(BaseModel):
    id: int
    title: str
    comment_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BlogPostBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class BlogPostResponse(BlogPostBase):
    id: int
    created_at: datetime
    updated_at: datetime
    comments: List[CommentResponse] = []
    
    class Config:
        from_attributes = True


class BlogPostCreate(BlogPostBase):
    pass


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


@app.get("/api/posts/{post_id}", response_model=BlogPostResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post with id {post_id} not found"
        )
    
    return post


@app.post("/api/posts", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(post_data: BlogPostCreate, db: Session = Depends(get_db)):
    db_post = BlogPost(
        title=post_data.title,
        content=post_data.content
    )
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    return db_post


@app.post(
    "/api/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_comment(
    post_id: int, 
    comment_data: CommentCreate, 
    db: Session = Depends(get_db)
):
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blog post with id {post_id} not found"
        )
    
    db_comment = Comment(
        content=comment_data.content,
        author=comment_data.author,
        blog_post_id=post_id
    )
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    return db_comment


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # TODO: Disable in production
        log_level="info"
    )
