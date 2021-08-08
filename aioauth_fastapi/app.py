from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from .users.backends import JWTAuthBackend
from .events import on_shutdown, on_startup
from .config import settings

from .containers import ApplicationContainer

from .users import endpoints as users_endpoint

from starlette.middleware.authentication import AuthenticationMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    on_startup=on_startup,
    on_shutdown=on_shutdown,
)

container = ApplicationContainer()
app.container = container
app.container.init_resources()
app.container.wire(modules=[users_endpoint])


# Include API router
app.include_router(users_endpoint.router, prefix="/api/users")
app.add_middleware(AuthenticationMiddleware, backend=JWTAuthBackend())