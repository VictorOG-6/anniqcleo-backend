from fastapi import FastAPI
from routers import auth, user, product, cart, order, review, dashboard
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY"),
    session_cookie="session",
    max_age=3600,
    same_site="lax",
    https_only=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

@app.get("/health")
def health():
    return {'status': 'ok'}

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(product.router)
app.include_router(cart.router)
app.include_router(order.router)
app.include_router(review.router)
app.include_router(dashboard.router)