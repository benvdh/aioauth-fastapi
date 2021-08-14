from aioauth_fastapi.users.crypto import get_jwt
from aioauth_fastapi.users.tables import UserTable
from typing import Optional
from aioauth_fastapi.storage.db import Database
from aioauth.requests import Request
from aioauth.models import Token, AuthorizationCode, Client
from .tables import ClientTable, AuthorizationCodeTable, TokenTable
from sqlalchemy.future import select
from aioauth.storage import BaseStorage
from ..users.models import User


class OAuth2Repository(BaseStorage):
    def __init__(self, database: Database):
        self.database = database

    async def get_user(self, request: Request):
        user = None

        if request.user:
            # authorization flow
            user = request.user
        else:
            # for grant_type token
            async with self.database.session() as session:
                q = select(AuthorizationCodeTable).where(
                    AuthorizationCodeTable.code == request.post.code
                )
                results = await session.execute(q)
                authorization_code_record = results.scalars().one_or_none()
                user_id = authorization_code_record.user_id

                q = select(UserTable).where(UserTable.id == user_id)

                results = await session.execute(q)
                user_record = results.scalars().one_or_none()

                user = User.from_orm(user_record)

        return user

    async def create_token(self, request: Request, client_id: str, scope: str) -> Token:
        user = await self.get_user(request)

        access_token, refresh_token = get_jwt(user)

        token = await super().create_token(request, client_id, scope)

        token_params = {
            **token._asdict(),
            # Replace aioauth access/refresh tokens to JWT
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

        return Token(**token_params)

    async def save_token(self, request: Request, token: Token) -> None:
        token_record = TokenTable(
            **{
                **token._asdict(),
                "user_id": request.user.id,
            }
        )
        async with self.database.session() as session:
            session.add(token_record)
            await session.commit()

    async def revoke_token(self, request: Request, refresh_token: str) -> None:
        """
        Remove refresh_token from whitelist.
        """

    async def get_token(
        self,
        request: Request,
        client_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> Optional[Token]:
        ...

    async def get_id_token(
        self,
        request: Request,
        client_id: str,
        scope: str,
        response_type: str,
        redirect_uri: str,
        nonce: str,
    ) -> str:
        return await super().get_id_token(
            request, client_id, scope, response_type, redirect_uri, nonce
        )

    async def save_authorization_code(
        self, request: Request, authorization_code: AuthorizationCode
    ) -> None:
        authorization_code_record = AuthorizationCodeTable(
            **{
                **authorization_code._asdict(),
                "user_id": request.user.id,
            }
        )

        async with self.database.session() as session:
            session.add(authorization_code_record)
            await session.commit()

    async def get_client(
        self, request: Request, client_id: str, client_secret: Optional[str] = None
    ) -> Optional[Client]:
        q = select(ClientTable).where(ClientTable.client_id == client_id)
        async with self.database.session() as session:
            results = await session.execute(q)
            one = results.scalars().one_or_none()

        if one is not None:
            return Client(
                client_id=one.client_id,
                client_secret=one.client_secret,
                grant_types=one.grant_types,
                response_types=one.response_types,
                redirect_uris=one.redirect_uris,
                scope=one.scope,
            )

    async def authenticate(self, request: Request) -> bool:
        return await super().authenticate(request)

    async def get_authorization_code(
        self, request: Request, client_id: str, code: str
    ) -> Optional[AuthorizationCode]:
        q = select(AuthorizationCodeTable).where(AuthorizationCodeTable.code == code)

        async with self.database.session() as session:
            results = await session.execute(q)
            one = results.scalars().one_or_none()

        if one is not None:
            return AuthorizationCode(
                code=one.code,
                client_id=one.client_id,
                redirect_uri=one.redirect_uri,
                response_type=one.response_type,
                scope=one.scope,
                auth_time=one.auth_time,
                expires_in=one.expires_in,
                code_challenge=one.code_challenge,
                code_challenge_method=one.code_challenge_method,
                nonce=one.nonce,
            )

    async def delete_authorization_code(
        self, request: Request, client_id: str, code: str
    ) -> None:
        q = select(AuthorizationCodeTable).where(AuthorizationCodeTable.code == code)

        async with self.database.session() as session:
            results = await session.execute(q)
            one = results.scalars().one_or_none()

            await session.delete(one)