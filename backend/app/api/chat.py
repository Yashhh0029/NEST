from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageUpdate,
)
from app.services import chat_service

router = APIRouter(tags=["Chat & Messaging"])


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve conversation for an active connection",
    description="Initializes a conversation for an accepted connection. If one already exists, returns the existing record idempotently.",
)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    conversation = chat_service.create_conversation(
        db,
        payload.connection_id,
        current_user.id,
    )
    return chat_service.format_conversation_response(
        conversation,
        current_user.id,
        db,
    )


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all active conversations",
    description="Returns all conversations belonging to the authenticated user for active accepted connections.",
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationListResponse:
    conversations = chat_service.list_conversations(db, current_user.id)
    return ConversationListResponse(
        total=len(conversations),
        conversations=conversations,
    )


@router.get(
    "/conversations/by-connection/{connection_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve conversation by connection ID (retrieve-only)",
    description="Retrieve-only endpoint that gets the existing conversation for a connection. Does NOT create database records. Returns 404 if not yet created.",
)
def get_conversation_by_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    conversation = chat_service.get_conversation_by_connection_id(
        db,
        connection_id,
        current_user.id,
    )
    return chat_service.format_conversation_response(
        conversation,
        current_user.id,
        db,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get conversation by ID",
)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    conversation, _ = chat_service.verify_conversation_access(
        db,
        conversation_id,
        current_user.id,
    )
    return chat_service.format_conversation_response(
        conversation,
        current_user.id,
        db,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated messages in a conversation",
)
def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = Query(None, description="Fetch messages created before this timestamp"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageListResponse:
    return chat_service.get_conversation_messages(
        db,
        conversation_id,
        current_user.id,
        limit=limit,
        before_timestamp=before,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to a conversation",
)
def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    message = chat_service.send_message(
        db,
        conversation_id,
        current_user.id,
        payload,
    )
    return chat_service.format_message_response(message, current_user.id)


@router.patch(
    "/messages/{message_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit a message (author only)",
)
def edit_message(
    message_id: uuid.UUID,
    payload: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    message = chat_service.edit_message(
        db,
        message_id,
        current_user.id,
        payload,
    )
    return chat_service.format_message_response(message, current_user.id)


@router.delete(
    "/messages/{message_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a message (author only)",
)
def delete_message(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    message = chat_service.delete_message(
        db,
        message_id,
        current_user.id,
    )
    return chat_service.format_message_response(message, current_user.id)
