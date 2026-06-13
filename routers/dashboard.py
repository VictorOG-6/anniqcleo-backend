from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from sqlmodel import select

from database import SessionDep
from models import (
    DashboardSummary,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    TopSellingProduct,
    User,
)
from services.access_token import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def get_month_ranges():
    now = datetime.now(timezone.utc)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if current_month_start.month == 1:
        previous_month_start = current_month_start.replace(
            year=current_month_start.year - 1,
            month=12,
        )
    else:
        previous_month_start = current_month_start.replace(
            month=current_month_start.month - 1,
        )

    return previous_month_start, current_month_start, now


def calculate_percentage_change(current_value: int, previous_value: int) -> float | None:
    if previous_value == 0:
        return None
    return round(((current_value - previous_value) / previous_value) * 100, 2)


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    previous_month_start, current_month_start, now = get_month_ranges()

    current_revenue = session.exec(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= current_month_start,
            Order.created_at < now,
        )
    ).one()
    previous_revenue = session.exec(
        select(func.coalesce(func.sum(Order.total_price), 0)).where(
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= previous_month_start,
            Order.created_at < current_month_start,
        )
    ).one()

    current_orders = session.exec(
        select(func.count(Order.id)).where(
            Order.created_at >= current_month_start,
            Order.created_at < now,
        )
    ).one()
    previous_orders = session.exec(
        select(func.count(Order.id)).where(
            Order.created_at >= previous_month_start,
            Order.created_at < current_month_start,
        )
    ).one()

    current_customers = session.exec(
        select(func.count(User.id)).where(
            User.created_at >= current_month_start,
            User.created_at < now,
        )
    ).one()
    previous_customers = session.exec(
        select(func.count(User.id)).where(
            User.created_at >= previous_month_start,
            User.created_at < current_month_start,
        )
    ).one()
    total_products = session.exec(
    select(func.count(Product.id)).where(
            Product.status == ProductStatus.PUBLISHED
        )
    ).one()

    return DashboardSummary(
        total_revenue=current_revenue,
        revenue_change_percent=calculate_percentage_change(
            current_revenue,
            previous_revenue,
        ),
        total_orders=current_orders,
        orders_change_percent=calculate_percentage_change(
            current_orders,
            previous_orders,
        ),
        total_customers=current_customers,
        customers_change_percent=calculate_percentage_change(
            current_customers,
            previous_customers,
        ),
        total_products=total_products,
    )


@router.get("/top-products", response_model=list[TopSellingProduct])
def get_top_selling_products(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    limit: int = Query(5, ge=1, le=50),
):
    statement = (
        select(
            Product,
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.price_at_purchase), 0),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status == OrderStatus.COMPLETED)
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .options(selectinload(Product.variants))
        .limit(limit)
    )

    products = session.exec(statement).all()
    return [
        TopSellingProduct(
            product=product,
            quantity_sold=quantity_sold,
            revenue=revenue,
        )
        for product, quantity_sold, revenue in products
    ]
