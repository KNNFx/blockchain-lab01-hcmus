# messages.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional


class MessageType(Enum):
    TX = auto()
    BLOCK_HEADER = auto()
    BLOCK_BODY = auto()
    VOTE = auto()
    GET_BLOCK = auto()


@dataclass
class Message:
    """
    Message cơ bản đi qua mạng:
    - from_id: node gửi
    - to_id: node nhận
    - payload: nội dung (tx, block, vote, ...)
    - msg_type: loại message
    - height: optional, dùng cho log & consensus
    """
    msg_id: int
    from_id: str
    to_id: str
    msg_type: MessageType
    payload: Any
    height: Optional[int] = None
