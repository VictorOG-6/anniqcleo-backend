from fastapi import APIRouter, status, Depends, Query, HTTPException
from models import ProductRead, ProductCreate, Product, ProductUpdate, ProductVariant, User, ProductStatus, ProductCategorySummary, OrderItem
from database import SessionDep
from services.access_token import get_current_user
from typing import Optional
from sqlmodel import select, col
from sqlalchemy import func
import re

router = APIRouter(prefix="/product", tags=["Products"])

def slugify_product_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "product"

def generate_unique_product_slug(session: SessionDep, name: str, product_id: Optional[str] = None) -> str:
    base_slug = slugify_product_name(name)
    slug = base_slug
    suffix = 1

    while True:
        statement = select(Product).where(Product.slug == slug)
        if product_id is not None:
            statement = statement.where(Product.id != product_id)

        existing_product = session.exec(statement).first()
        if not existing_product:
            return slug

        suffix += 1
        slug = f"{base_slug}-{suffix}"

@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, session: SessionDep, current_user: User = Depends(get_current_user)):
    # Extract variants before creating product
    variants_data = product.variants or []
    product_data = product.model_dump(exclude={"variants"})
    product_data["slug"] = generate_unique_product_slug(session, product.name)

    new_product = Product(**product_data)
    new_product.variants = [ProductVariant(color=c) for c in variants_data]

    session.add(new_product)
    session.commit()
    session.refresh(new_product)
    return new_product

@router.get("", response_model=list[ProductRead])
def get_products(
    session: SessionDep, 
    name: Optional[str] = Query(None, description="Filter products by name (partial match)"),
    category: Optional[str] = Query(None, description="Filter products by category (partial match)"),
    status: Optional[ProductStatus] = Query(None, description="Filter products by status"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(10, description="Number of items per page", ge=1, le=100),
    ):
    
    statement = select(Product)

    if (name):
        statement = statement.where(col(Product.name).contains(name))

    if (category):
        statement = statement.where(Product.category == category)

    if (status):
        statement = statement.where(Product.status == status)
    
    products = session.exec(statement).all()
    return products

@router.get("/categories/summary", response_model=list[ProductCategorySummary])
def get_product_categories_summary(
    session: SessionDep,
    status: Optional[ProductStatus] = Query(None, alias="status"),
):
    statement = (
        select(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .order_by(Product.category)
    )

    if status:
        statement = statement.where(Product.status == status)

    categories = session.exec(statement).all()
    return [
        ProductCategorySummary(category=category, product_count=count)
        for category, count in categories
    ]

@router.get("/{product_id}", response_model=ProductRead)
def get_product_by_id(product_id: str, session: SessionDep, current_user: User = Depends(get_current_user)):
    product = session.exec(select(Product).where(Product.id == product_id)).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductRead, status_code=status.HTTP_202_ACCEPTED)
def update_product(product_id: str, product_update: ProductUpdate, session: SessionDep, current_user: User = Depends(get_current_user)):
    updated_product = session.exec(select(Product).where(Product.id == product_id)).first()
    if not updated_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Update scalar fields only
    product_data = product_update.model_dump(exclude_unset=True, exclude={"variants"})
    if product_data.get("name") is not None:
        product_data["slug"] = generate_unique_product_slug(session, product_data["name"], product_id)
    updated_product.sqlmodel_update(product_data)

    # Sync variants only if explicitly provided
    if product_update.variants is not None:
        for variant in updated_product.variants:
            session.delete(variant)
        session.flush()  # ensure deletes run before inserts
        updated_product.variants = [ProductVariant(color=c) for c in product_update.variants]

    session.add(updated_product)
    session.commit()
    session.refresh(updated_product)
    return updated_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    product = session.exec(
        select(Product).where(Product.id == product_id)
    ).first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    has_orders = session.exec(
        select(OrderItem.id).where(
            OrderItem.product_id == product_id
        )
    ).first()

    if has_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product has existing orders and cannot be deleted. "
                "Archive it instead."
            )
        )

    session.delete(product)
    session.commit()

    return None