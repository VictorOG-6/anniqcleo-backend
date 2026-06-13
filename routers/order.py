from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import selectinload
from sqlmodel import select, col
from models import Order, OrderRead, OrderItem, Cart, CartItem, User, OrderStatus
from database import SessionDep
from services.access_token import get_current_user
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

router = APIRouter(prefix="/order", tags=["Orders"])

def process_order_refund(order: Order) -> bool:
    # Replace this with the third-party payment provider refund call.
    return True

def generate_next_order_public_id(session: SessionDep) -> str:
    public_ids = session.exec(select(Order.public_id)).all()
    highest_number = 0

    for public_id in public_ids:
        if not public_id.startswith("ord-"):
            continue

        try:
            order_number = int(public_id.removeprefix("ord-"))
        except ValueError:
            continue

        highest_number = max(highest_number, order_number)

    return f"ord-{highest_number + 1:04d}"

@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    # 1. Load cart snapshot
    cart = session.exec(
        select(Cart)
        .where(Cart.user_id == current_user.id)
        .options(
            selectinload(Cart.items).selectinload(CartItem.product)
        )
    ).first()
    if not cart or not cart.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )
    # 2. Build order items from cart items
    order_items: list[OrderItem] = []
    for cart_item in cart.items:
        product = cart_item.product
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {cart_item.product_id} not found",
            )
        order_items.append(
            OrderItem(
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price_at_purchase=product.price,  # snapshot unit price
            )
        )
    # 3. Compute totals from order_items (not from cart directly)
    total_products = sum(item.quantity for item in order_items)
    total_price = sum(item.quantity * item.price_at_purchase for item in order_items)
    # 4. Create order
    order = Order(
        public_id=generate_next_order_public_id(session),
        user_id=current_user.id,
        total_price=total_price,
        total_products=total_products,
    )
    session.add(order)
    session.flush()  # get order.id before linking items
    # 5. Attach items to order
    for item in order_items:
        item.order_id = order.id
        session.add(item)
    # 6. Optional: clear cart after successful checkout
    for cart_item in cart.items:
        session.delete(cart_item)
    session.commit()
    session.refresh(order)
    # Eager-load relationships for response
    order = session.exec(
        select(Order)
        .where(Order.id == order.id)
        .options(
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.user),
        )
    ).one()
    return order

@router.get("", response_model=list[OrderRead])
def get_orders(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(10, description="Number of items per page", ge=1, le=100),
    status: Optional[OrderStatus] = Query(None, description="Filter orders by status"),
    name: Optional[str] = Query(
        None,
        description="Filter orders by the name of the user who owns the order (partial match)",
    ),
):
    statement = (
        select(Order)
        .join(User, Order.user_id == User.id)
        .options(
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.user),
        )
        .order_by(Order.created_at.desc())
    )

    if status:
        statement = statement.where(Order.status == status)

    if name:
        statement = statement.where(col(User.name).contains(name))

    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size)

    orders = session.exec(statement).all()
    return orders

@router.patch("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    order = session.exec(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.user),
        )
    ).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order.status not in {OrderStatus.PENDING, OrderStatus.PROCESSING}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or processing orders can be cancelled",
        )

    now = datetime.now(timezone.utc)
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = now
    session.add(order)
    session.commit()
    session.refresh(order)

    if not process_order_refund(order):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Order cancelled, but refund could not be completed",
        )

    order.status = OrderStatus.REFUNDED
    order.refunded_at = datetime.now(timezone.utc)
    session.add(order)
    session.commit()
    session.refresh(order)

    return order

@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: UUID,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    order = session.exec(
        select(Order)
        .where(Order.id == order_id, Order.user_id == current_user.id)
        .options(
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.user),
        )
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order