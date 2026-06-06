from fastapi import APIRouter, Depends, HTTPException, status, Query
from models import Review, ReviewCreate, ReviewRead, ReviewUpdate, User
from database import SessionDep
from services.access_token import get_current_user
from sqlmodel import select
from uuid import UUID
from typing import Optional

router = APIRouter(prefix="/review", tags=["Reviews"])

@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(review: ReviewCreate, session: SessionDep, current_user: User = Depends(get_current_user)):
    new_review = Review(**review.model_dump())
    session.add(new_review)
    session.commit()
    session.refresh(new_review)
    return new_review

@router.get("", response_model=list[ReviewRead])
def get_reviews(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    product_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(50, description="Number of items per page", ge=1, le=100),
    ):
    statement = select(Review).where(Review.user_id == current_user.id)
    if (product_id):
        statement = statement.where(Review.product_id == product_id)
    if (user_id):
        statement = statement.where(Review.user_id == user_id)
    reviews = session.exec(statement).all()
    return reviews

@router.put("/{review_id}", response_model=ReviewRead, status_code=status.HTTP_202_ACCEPTED)
def update_review(review_id: UUID, review_update: ReviewUpdate, session: SessionDep, current_user: User = Depends(get_current_user)):
    updated_review = session.exec(select(Review).where(Review.id == review_id, Review.user_id == current_user.id)).first()
    if not updated_review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    review_data = review_update.model_dump(exclude_unset=True)
    updated_review.sqlmodel_update(review_data)

    session.add(updated_review)
    session.commit()
    session.refresh(updated_review)
    return updated_review

@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: UUID, session: SessionDep, current_user: User = Depends(get_current_user)):
    deleted_review = session.exec(select(Review).where(Review.id == review_id, Review.user_id == current_user.id)).first()
    if not deleted_review:
        raise HTTPException(status_code=404, detail="Review not found")
    session.delete(deleted_review)
    session.commit()
    return None