from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from models import Order, OrderItem, Product, ProductVariant


def _load_inventory(
    session: Session,
    order: Order,
) -> tuple[list[OrderItem], dict[UUID, Product], dict[UUID, ProductVariant]]:
    items = list(
        session.exec(
            select(OrderItem)
            .where(OrderItem.order_id == order.id)
            .order_by(OrderItem.id)
            .with_for_update()
        ).all()
    )
    product_ids = sorted({item.product_id for item in items}, key=str)
    products = list(
        session.exec(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        ).all()
    )
    variants = list(
        session.exec(
            select(ProductVariant)
            .where(ProductVariant.product_id.in_(product_ids))
            .order_by(ProductVariant.id)
            .with_for_update()
        ).all()
    )
    return (
        items,
        {product.id: product for product in products},
        {variant.id: variant for variant in variants},
    )


def commit_inventory_for_order(session: Session, order: Order) -> None:
    if order.inventory_committed_at is not None:
        return

    items, products, variants = _load_inventory(session, order)
    variants_by_product: dict[UUID, list[ProductVariant]] = defaultdict(list)
    for variant in variants.values():
        variants_by_product[variant.product_id].append(variant)

    product_demand: dict[UUID, int] = defaultdict(int)
    variant_demand: dict[UUID, int] = defaultdict(int)

    for item in items:
        product = products.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product {item.product_id} is no longer available",
            )

        product_variants = variants_by_product[item.product_id]
        if product_variants:
            if item.product_variant_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A variant is required for product {product.name}",
                )
            variant = variants.get(item.product_variant_id)
            if not variant or variant.product_id != item.product_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The selected variant for {product.name} is invalid",
                )
            variant_demand[variant.id] += item.quantity
        else:
            if item.product_variant_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The selected variant for {product.name} is unavailable",
                )
            product_demand[product.id] += item.quantity

    for variant_id, quantity in variant_demand.items():
        variant = variants[variant_id]
        if variant.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {variant.quantity} units of {variant.name} are available",
            )

    for product_id, quantity in product_demand.items():
        product = products[product_id]
        if product.quantity < quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only {product.quantity} units of {product.name} are available",
            )

    for variant_id, quantity in variant_demand.items():
        variants[variant_id].quantity -= quantity
    for product_id, quantity in product_demand.items():
        products[product_id].quantity -= quantity
    for product_id, product_variants in variants_by_product.items():
        products[product_id].quantity = sum(
            variant.quantity for variant in product_variants
        )

    order.inventory_committed_at = datetime.now(timezone.utc)
    session.add(order)


def restore_inventory_for_order(session: Session, order: Order) -> None:
    if (
        order.inventory_committed_at is None
        or order.inventory_restored_at is not None
    ):
        return

    items, products, variants = _load_inventory(session, order)
    variant_product_ids: set[UUID] = set()

    for item in items:
        product = products.get(item.product_id)
        if not product:
            continue
        if item.product_variant_id is None:
            product.quantity += item.quantity
            continue

        variant = variants.get(item.product_variant_id)
        if not variant or variant.product_id != item.product_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ordered variant is unavailable for inventory restoration",
            )
        variant.quantity += item.quantity
        variant_product_ids.add(item.product_id)

    for product_id in variant_product_ids:
        products[product_id].quantity = sum(
            variant.quantity
            for variant in variants.values()
            if variant.product_id == product_id
        )

    order.inventory_restored_at = datetime.now(timezone.utc)
    session.add(order)
