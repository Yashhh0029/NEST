import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.connection import Connection, ConnectionStatus
from app.models.conversation import Conversation, Message
from app.models.user import User

logger = logging.getLogger(__name__)
from app.schemas.chat import (
    ConversationResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
    MessageUpdate,
)
from app.schemas.connection import ConnectionRequestSummary, ConnectionUserSummary
from app.services.safety_service import is_blocked_bidirectional


def verify_connection_access(
    db: Session,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Connection:
    """
    Validate that connection exists, user is either requester or helper,
    and connection status is ACCEPTED.
    Raises 404 if connection not found, 403 if user not participant or connection inactive.
    """
    connection = db.query(Connection).filter(Connection.id == connection_id).first()
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found.",
        )

    if connection.requester_id != user_id and connection.helper_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this connection.",
        )

    allowed_statuses = [ConnectionStatus.ACCEPTED.value, ConnectionStatus.COMPLETED.value]
    if connection.status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Messaging is only allowed for active accepted or completed connections. Current status: {connection.status}.",
        )

    return connection


def verify_conversation_access(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Tuple[Conversation, Connection]:
    """
    Load conversation and associated connection, verifying that current user
    is either requester or helper AND the connection status is ACCEPTED.
    Raises 404 if conversation not found, 403 if forbidden.
    """
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    connection = verify_connection_access(db, conversation.connection_id, user_id)
    return conversation, connection


def build_user_summary(user: Optional[User]) -> ConnectionUserSummary:
    if not user:
        return ConnectionUserSummary(
            id=uuid.uuid4(),
            name="Unknown User",
            headline=None,
            city=None,
            area=None,
        )

    headline = user.profile.headline if user.profile else None
    city = None
    area = None
    if user.locations and len(user.locations) > 0:
        city = user.locations[0].city
        area = user.locations[0].area

    return ConnectionUserSummary(
        id=user.id,
        name=user.name,
        headline=headline,
        city=city,
        area=area,
    )


def format_message_response(
    message: Message,
    current_user_id: Optional[uuid.UUID] = None,
) -> MessageResponse:
    content = "Message deleted" if message.deleted_at is not None else message.content
    sender_name = message.sender.name if message.sender else "Community Member"
    is_mine = (message.sender_id == current_user_id) if current_user_id else None

    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_name=sender_name,
        content=content,
        is_read=message.is_read,
        is_mine=is_mine,
        created_at=message.created_at,
        updated_at=message.updated_at,
        edited_at=message.edited_at,
        deleted_at=message.deleted_at,
    )


def format_conversation_response(
    conversation: Conversation,
    current_user_id: uuid.UUID,
    db: Session,
) -> ConversationResponse:
    conn = conversation.connection
    is_requester = conn.requester_id == current_user_id
    partner_user = conn.helper if is_requester else conn.requester
    partner_summary = build_user_summary(partner_user)

    request_summary = None
    if conn.request:
        request_summary = ConnectionRequestSummary(
            id=conn.request.id,
            raw_text=conn.request.raw_text,
            city=conn.request.city,
            area=conn.request.area,
            intent=conn.request.intent,
        )

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(desc(Message.created_at))
        .first()
    )
    last_message_response = (
        format_message_response(last_msg, current_user_id) if last_msg else None
    )

    unread_count = (
        db.query(func.count(Message.id))
        .filter(
            Message.conversation_id == conversation.id,
            Message.sender_id != current_user_id,
            Message.is_read.is_(False),
            Message.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )

    return ConversationResponse(
        id=conversation.id,
        connection_id=conversation.connection_id,
        connection_status=conn.status,
        partner=partner_summary,
        request=request_summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        last_message=last_message_response,
        unread_count=unread_count,
    )


def create_conversation(
    db: Session,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation:
    """
    Create a conversation for an active accepted connection.
    Idempotent: if conversation already exists, returns it without creating duplicate.
    """
    connection = verify_connection_access(db, connection_id, user_id)

    if is_blocked_bidirectional(db, connection.requester_id, connection.helper_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action not permitted due to safety restrictions.",
        )

    # Check for existing conversation
    existing = (
        db.query(Conversation)
        .filter(Conversation.connection_id == connection.id)
        .first()
    )
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    conversation = Conversation(
        id=uuid.uuid4(),
        connection_id=connection.id,
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation_by_connection_id(
    db: Session,
    connection_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation:
    """
    Retrieve-only function: gets the conversation for a connection.
    Does NOT create any database records. Returns 404 if not yet created.
    """
    verify_connection_access(db, connection_id, user_id)
    conversation = (
        db.query(Conversation)
        .filter(Conversation.connection_id == connection_id)
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation has not been initiated for this connection yet.",
        )
    return conversation


def list_conversations(
    db: Session,
    user_id: uuid.UUID,
) -> List[ConversationResponse]:
    """
    List all conversations for the user where the associated connection is ACCEPTED.
    """
    conversations = (
        db.query(Conversation)
        .join(Connection, Conversation.connection_id == Connection.id)
        .filter(
            or_(
                Connection.requester_id == user_id,
                Connection.helper_id == user_id,
            ),
            Connection.status.in_([
                ConnectionStatus.ACCEPTED.value,
                ConnectionStatus.COMPLETED.value,
            ]),
        )
        .order_by(desc(Conversation.updated_at))
        .all()
    )

    return [
        format_conversation_response(c, user_id, db)
        for c in conversations
    ]


def get_conversation_messages(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 50,
    before_timestamp: Optional[datetime] = None,
) -> MessageListResponse:
    """
    Fetch paginated messages in ascending chronological order for the view.
    Marks partner unread messages as read.
    """
    conversation, _ = verify_conversation_access(db, conversation_id, user_id)

    query = db.query(Message).filter(Message.conversation_id == conversation.id)
    if before_timestamp:
        query = query.filter(Message.created_at < before_timestamp)

    # Order by desc to get latest window, then reverse to chronological order
    total = query.count()
    raw_messages = query.order_by(desc(Message.created_at)).limit(limit + 1).all()

    has_more = len(raw_messages) > limit
    messages_to_return = raw_messages[:limit]
    # Reverse so frontend renders oldest -> newest
    messages_to_return.reverse()

    # Mark unread incoming messages as read
    unread_incoming = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id,
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .all()
    )
    if unread_incoming:
        for msg in unread_incoming:
            msg.is_read = True
        db.commit()

    formatted = [
        format_message_response(m, user_id) for m in messages_to_return
    ]
    return MessageListResponse(
        total=total,
        has_more=has_more,
        messages=formatted,
    )


def send_message(
    db: Session,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MessageCreate,
) -> Message:
    """
    Persist a new message from authenticated user to PostgreSQL.
    Verifies user is participant and connection is ACCEPTED.
    """
    conversation, connection = verify_conversation_access(db, conversation_id, user_id)

    if is_blocked_bidirectional(db, connection.requester_id, connection.helper_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action not permitted due to safety restrictions.",
        )

    if connection.status == ConnectionStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This interaction is completed. New messages cannot be sent.",
        )

    now = datetime.now(timezone.utc)
    message = Message(
        id=uuid.uuid4(),
        conversation_id=conversation.id,
        sender_id=user_id,
        content=payload.content,
        is_read=False,
        created_at=now,
        updated_at=now,
    )
    db.add(message)

    # Update conversation updated_at timestamp
    conversation.updated_at = now
    db.commit()
    db.refresh(message)

    # Check recipient online presence and dispatch email notification if recipient is offline
    try:
        recipient_id = connection.helper_id if user_id == connection.requester_id else connection.requester_id
        recipient = connection.helper if user_id == connection.requester_id else connection.requester
        if recipient and recipient.email and recipient.email_verified and recipient.is_active:
            from app.services.notification_service import is_user_actively_online
            if not is_user_actively_online(recipient_id, conversation.id):
                from app.services.email_service import dispatch_email_async, render_new_message_email
                frontend_base = settings.FRONTEND_URL.rstrip("/")
                conv_url = f"{frontend_base}/connections"
                safe_preview = payload.content[:100] + ("..." if len(payload.content) > 100 else "")
                sender_user = db.query(User).filter(User.id == user_id).first()
                sender_name = sender_user.name if sender_user else "A community member"
                html_body, text_body = render_new_message_email(
                    recipient_name=recipient.name or "Neighbor",
                    sender_name=sender_name,
                    message_preview=safe_preview,
                    conversation_url=conv_url,
                )
                idempotency_key = f"chat_msg_{message.id}_{recipient_id}"
                dispatch_email_async(
                    to_email=recipient.email,
                    subject=f"You have a new message on NEST from {sender_name}",
                    html_body=html_body,
                    text_body=text_body,
                    idempotency_key=idempotency_key,
                    recipient_id=recipient_id,
                    notification_type="new_message",
                    metadata_payload={
                        "conversation_id": str(conversation.id),
                        "message_id": str(message.id),
                        "sender_id": str(user_id),
                    },
                )
    except Exception as exc:
        logger.warning("Failed to dispatch offline chat email notification: %s", exc)

    return message


def edit_message(
    db: Session,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MessageUpdate,
) -> Message:
    """
    Edit a message. Only the original sender can edit.
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    # Verify connection is still active and user has access
    verify_conversation_access(db, message.conversation_id, user_id)

    if message.sender_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages.",
        )

    if message.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a deleted message.",
        )

    now = datetime.now(timezone.utc)
    message.content = payload.content
    message.edited_at = now
    message.updated_at = now
    db.commit()
    db.refresh(message)
    return message


def delete_message(
    db: Session,
    message_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Message:
    """
    Soft-delete a message. Only the original sender can delete.
    Preserves conversation structure by populating deleted_at.
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    # Verify conversation access
    verify_conversation_access(db, message.conversation_id, user_id)

    if message.sender_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages.",
        )

    now = datetime.now(timezone.utc)
    message.deleted_at = now
    message.updated_at = now
    db.commit()
    db.refresh(message)
    return message
