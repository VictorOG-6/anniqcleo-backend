from sqlmodel import Field, SQLModel, Relationship
from typing import Optional
from datetime import datetime, timezone
from pydantic import EmailStr
from uuid import UUID, uuid4
from sqlalchemy import Column, DateTime
from enum import Enum
from pwdlib import PasswordHash
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import func

password_hash = PasswordHash.recommended()

class GoogleUser(SQLModel):
    sub: str
    email: EmailStr
    email_verified: bool = False
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None

class UserBase(SQLModel):
    name: Optional[str] = Field(default=None)
    email: EmailStr = Field(unique=True, index=True)

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    STAFF = "staff"
    
class User(UserBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    hashed_password: Optional[str] = None
    google_sub: Optional[str] = Field(default=None, unique=True, index=True)
    profile_image_url: Optional[str] = Field(default=None, max_length=500)
    cart: "Cart" = Relationship(back_populates="user")
    orders: list["Order"] = Relationship(back_populates="user")
    reviews: list["Review"] = Relationship(back_populates="user")
    total_orders: int = Field(default=0)
    total_spent: int = Field(default=0)
    role: UserRole = Field(default=UserRole.USER)

class UserRead(UserBase):
    id: UUID
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    orders: list["OrderRead"]
    reviews: list["ReviewRead"]
    cart: "CartRead"
    total_orders: int
    total_spent: int
    role: UserRole

class UserCreate(UserBase):
    profile_image_url: Optional[str] = Field(default=None)
    password: str

class UserUpdate(UserBase):
    name: Optional[str] = Field(default=None, min_length=2)
    email: Optional[EmailStr] = None
    profile_image_url: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)

class Login(SQLModel):
    username: str
    password: str

class Token(SQLModel):
    access_token: str
    token_type: str
    refresh_token: str

class TokenData(SQLModel):
    username: Optional[str] = None
    user_id: Optional[str] = None
    jti: Optional[str] = None

class RefreshTokenRequest(SQLModel):
    refresh_token: str

class RefreshToken(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    token: str = Field(unique=True, index=True)
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    revoked: bool = Field(default=False)

class UserAuthRead(UserBase):
    id: UUID
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    total_orders: int
    total_spent: int
    role: UserRole

class AuthModel(SQLModel):
    user: UserAuthRead
    access_token: str
    refresh_token: str
    token_type: str

class ProductStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class ProductVariant(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    product_id: UUID = Field(foreign_key="product.id", nullable=False)
    color: str
    product: Optional["Product"] = Relationship(back_populates="variants")

class ProductVariantRead(SQLModel):
    id: UUID
    product_id: UUID
    color: str
    product: "ProductRead"

class ProductBase(SQLModel):
    name: str
    image_url: str
    price: int
    category: str
    description: str

class Product(ProductBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    slug: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
         sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    reviews: list["Review"] = Relationship(back_populates="product")
    total_reviews: int
    average_rating: int
    variants: list["ProductVariant"] = Relationship(back_populates="product")
    order_items: list["OrderItem"] = Relationship(back_populates="product")
    cart_items: list["CartItem"] = Relationship(back_populates="product")
    status: ProductStatus = Field(default=ProductStatus.DRAFT)

class ProductCreate(ProductBase):
    variants: Optional[list[str]] = None
    status: ProductStatus = ProductStatus.DRAFT

class ProductRead(ProductBase):
    id: UUID
    slug: str
    created_at: datetime
    updated_at: datetime
    total_reviews: int
    average_rating: int
    variants: list["ProductVariantRead"]
    status: ProductStatus

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[list[str]] = None
    status: Optional[ProductStatus] = None

class DashboardSummary(SQLModel):
    total_revenue: int
    revenue_change_percent: Optional[float] = None
    total_orders: int
    orders_change_percent: Optional[float] = None
    total_customers: int
    customers_change_percent: Optional[float] = None
    total_products: int

class TopSellingProduct(SQLModel):
    product: ProductRead
    quantity_sold: int
    revenue: int

class ProductCategorySummary(SQLModel):
    category: str
    product_count: int

class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"
    COMPLETED = "completed"

class Order(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    public_id: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory= lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    order_items: list["OrderItem"] = Relationship(back_populates="order")
    total_price: int
    total_products: int
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    user: Optional["User"] = Relationship(back_populates="orders")
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    cancelled_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    refunded_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

class OrderRead(SQLModel):
    id: UUID
    public_id: str
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    order_items: list["OrderItemRead"]
    total_price: int
    total_products: int
    status: OrderStatus
    cancelled_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None

class OrderItem(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    order_id: UUID = Field(foreign_key="order.id", nullable=False)
    order: Optional["Order"] = Relationship(back_populates="order_items")
    product_id: UUID = Field(foreign_key="product.id", nullable=False)
    product: Optional["Product"] = Relationship(back_populates="order_items")
    quantity: int = 1
    price_at_purchase: int

class OrderItemRead(SQLModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    order_id: UUID
    product_id: UUID
    product: "ProductRead"
    quantity: int
    price_at_purchase: int
    
class Cart(SQLModel, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    user: Optional["User"] = Relationship(back_populates="cart")
    items: list["CartItem"] = Relationship(back_populates="cart")
    total_price: int
    total_products: int

class CartRead(SQLModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    user: "UserRead"
    items: list["CartItemRead"]
    total_price: int
    total_products: int

class CartItemBase(SQLModel):
    quantity: int = 1

class CartItem(CartItemBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    cart_id: UUID = Field(foreign_key="cart.id", nullable=False) 
    cart: Optional["Cart"] = Relationship(back_populates="items")
    product_id: UUID = Field(foreign_key="product.id", nullable=False)
    product: Optional["Product"] = Relationship(back_populates="cart_items")
    total_price: int
    
class CartItemCreate(CartItemBase):
    product_id: UUID

class CartItemUpdate(SQLModel):
    quantity: Optional[int] = None

class CartItemRead(CartItemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    cart_id: UUID
    product_id: UUID
    product: "ProductRead"
    total_price: int

class ReviewBase(SQLModel):
    rating: int
    comment: str

class Review(ReviewBase, table=True):
    id: Optional[UUID] = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, unique=True, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=func.now()),
    )
    user_id: UUID = Field(foreign_key="user.id", nullable=False)
    user: Optional["User"] = Relationship(back_populates="reviews")
    product_id: UUID = Field(foreign_key="product.id", nullable=False)
    product: Optional["Product"] = Relationship(back_populates="reviews")

class ReviewCreate(ReviewBase):
    product_id: UUID

class ReviewRead(ReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    user_id: UUID
    product_id: UUID
    product: "ProductRead"
    user: "UserRead"

class ReviewUpdate(SQLModel):
    rating: Optional[int] = None
    comment: Optional[str] = None 