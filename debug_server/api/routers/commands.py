# ruff: noqa: B008
"""Command queueing endpoints."""

from __future__ import annotations

import shlex

from fastapi import APIRouter, Depends, HTTPException, status

from debug_server.api.auth import BearerTokenAuth
from debug_server.api.context import AppContext, get_app_context
from debug_server.api.schemas import (
    CommandCreateRequest,
    CommandResponse,
    command_to_response,
)
from debug_server.db import AuthToken

router = APIRouter(prefix="/sessions/{session_id}/commands", tags=["commands"])


@router.post("", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
def queue_command(
    session_id: str,
    payload: CommandCreateRequest,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["commands:write", "sessions:write"])),
) -> CommandResponse:
    session = context.metadata_store.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found")
    command_repr = shlex.join(payload.argv)
    sequence = context.metadata_store.next_command_sequence(session_id)
    command = context.metadata_store.create_command(
        session_id=session_id,
        command=command_repr,
        cwd=payload.cwd,
        env=payload.env,
        sequence=sequence,
    )
    return command_to_response(command)


@router.get("", response_model=list[CommandResponse])
def list_commands(
    session_id: str,
    context: AppContext = Depends(get_app_context),
    _: AuthToken = Depends(BearerTokenAuth(["sessions:read"])),
) -> list[CommandResponse]:
    session = context.metadata_store.get_session(session_id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Session not found")
    commands = context.metadata_store.list_commands(session_id)
    return [command_to_response(cmd) for cmd in commands]


__all__ = ["router"]
