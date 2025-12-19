from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
from app.routers import users, auth, orders, products


def create_app() -> FastAPI:
    app = FastAPI(title="Canteen Backend")

    # -------------------------
    # 🔥 Request Body Logger
    # -------------------------
    # @app.middleware("http")
    # async def log_request(request: Request, call_next):
    #     body = await request.body()
    #     print("\n=== REQUEST BODY START ===")
    #     print(body.decode() or "<empty>")
    #     print("=== REQUEST BODY END ===\n")

    #     # Re-inject the body so downstream code can read it again
    #     async def receive():
    #         return {"type": "http.request", "body": body}

    #     request = Request(request.scope, receive=receive)

    #     response = await call_next(request)
    #     return response

    # Serve static files
    from fastapi.staticfiles import StaticFiles
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Include routers
    app.include_router(users.router)
    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(products.router)

    # Allowed origins
    origins = [
        "https://canteen-frontend-seller.web.app",
        "https://canteen-frontend-buyer.web.app",
        "http://localhost",
        "http://127.0.0.1"
    ]

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"http://localhost(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> str:
        return "ok"

    return app
