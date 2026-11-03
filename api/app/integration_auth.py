"""Bearer token for n8n (PF_N8N_TOKEN); /integrations/* accepts only this, ordinary APIs only accept sessions."""
import hmac
import os

from fastapi import HTTPException, Request

MIN_TOKEN_LENGTH = 24


def require_integration(request: Request) -> None:
    expected = os.environ.get('PF_N8N_TOKEN', '')
    scheme, _, token = request.headers.get('authorization', '').partition(' ')
    # An unset or short token disables the integration rather than accepting a guessable one.
    if len(expected) < MIN_TOKEN_LENGTH or scheme.lower() != 'bearer' or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail='整合服務驗證失敗')
