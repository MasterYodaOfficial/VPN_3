from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler

from slowapi.errors import RateLimitExceeded

from fastapi_app.api import subscription as api_router
from fastapi_app.core.limiter import limiter



app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    title="VPN Subscription Service"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.include_router(api_router.router, prefix="/api/v1/subscription", tags=["Subscription"])

@app.get("/")
@limiter.limit("10/minute")
def read_root(request: Request):
    return {"message": "Hi, don't hack me please, I,m the bad coder =)"}