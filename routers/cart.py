from fastapi import APIRouter, status, Depends, Query, HTTPException
from models import Cart, CartRead, CartItemCreate, CartItemRead, CartItem, CartItemUpdate, User
from database import SessionDep
from services.access_token import get_current_user
from typing import Optional
from sqlmodel import select, col
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/cart", tags=["Cart"])

@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
def create_cart_item(item: CartItemCreate, session: SessionDep, current_user: User = Depends(get_current_user)):
    new_item = CartItem(**item.model_dump())
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    return new_item

@router.get("", response_model=CartRead)
def get_cart(
    session: SessionDep, 
    current_user: User = Depends(get_current_user),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(10, description="Number of items per page", ge=1, le=100),
    ):
    
    statement = select(Cart).where(Cart.user_id == current_user.id).options(selectinload(Cart.items).selectinload(CartItem.product))
    
    cart = session.exec(statement).first()
    
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    total_products = sum(item.quantity for item in cart.items)
    total_price = sum(item.total_price for item in cart.items)

    cart.total_products = total_products
    cart.total_price = total_price

    session.add(cart)
    session.commit()
    session.refresh(cart)

    return cart

@router.put("/items/{item_id}", response_model=CartItemRead, status_code=status.HTTP_202_ACCEPTED)
def update_cart_item(item_id: str, item_update: CartItemUpdate, session: SessionDep, current_user: User = Depends(get_current_user)):
    updated_item = session.exec(select(CartItem).where(CartItem.id == item_id)).first()
    if not updated_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart Item not found")
    item_data = item_update.model_dump(exclude_unset=True)
    updated_item.sqlmodel_update(item_data)
    session.add(updated_item)
    session.commit()
    session.refresh(updated_item)
    return updated_item

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cart_item(item_id: str, session:SessionDep, current_user: User = Depends(get_current_user)):
    deleted_item = session.exec(select(CartItem).where(CartItem.id == item_id)).first()
    if not deleted_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart Item not found")
    session.delete(deleted_item)
    session.commit()
    return None