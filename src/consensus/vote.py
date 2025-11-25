from dataclasses import dataclass, asdict
from typing import Literal
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.crypto_layer import KeyPair, sign_struct, verify_struct

# Các giai đoạn bỏ phiếu (Vote phases)
PHASE_PREVOTE = "PREVOTE"
PHASE_PRECOMMIT = "PRECOMMIT"

@dataclass
class VoteBody:
    """
    Cấu trúc phiếu bầu chưa ký (unsigned), chứa thông tin cốt lõi.
    """
    height: int
    round: int
    block_hash: str  # Hash của block dưới dạng hex
    phase: Literal["PREVOTE", "PRECOMMIT"]
    validator_pubkey_hex: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Vote:
    """
    Phiếu bầu đã ký (signed).
    Bao gồm VoteBody cộng với chữ ký và thông tin xác thực.
    """
    height: int
    round: int
    block_hash: str
    phase: Literal["PREVOTE", "PRECOMMIT"]
    validator_pubkey_hex: str
    signature: str  # Chữ ký dạng hex
    pubkey: str     # Public key (phải khớp với validator_pubkey_hex)
    context: str    # Domain separation context

    @staticmethod
    def create(body: VoteBody, keypair: KeyPair) -> "Vote":
        """
        Tạo một phiếu bầu đã ký từ VoteBody sử dụng keypair của validator.
        """
        payload = body.to_dict()
        # Ký vào struct với prefix "VOTE:" để tránh replay attack
        signed_dict = sign_struct("VOTE:", keypair, payload)
        return Vote(**signed_dict)

    def verify(self) -> bool:
        """
        Kiểm tra chữ ký của phiếu bầu có hợp lệ không.
        """
        return verify_struct("VOTE:", asdict(self))
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: dict) -> "Vote":
        return Vote(**data)


def build_vote(
    height: int,
    round: int,
    block_hash: str,
    phase: Literal["PREVOTE", "PRECOMMIT"],
    keypair: KeyPair
) -> Vote:
    """
    Hàm tiện ích để tạo và ký phiếu bầu trong một bước.
    """
    body = VoteBody(
        height=height,
        round=round,
        block_hash=block_hash,
        phase=phase,
        validator_pubkey_hex=keypair.pubkey()
    )
    return Vote.create(body, keypair)


def verify_vote(vote: Vote) -> bool:
    """
    Xác thực phiếu bầu: kiểm tra chữ ký và tính nhất quán dữ liệu.
    """
    # 1. Check chữ ký
    if not vote.verify():
        return False
    
    # 2. Check pubkey khớp với người tạo phiếu
    if vote.pubkey != vote.validator_pubkey_hex:
        return False
    
    # 3. Check phase hợp lệ
    if vote.phase not in [PHASE_PREVOTE, PHASE_PRECOMMIT]:
        return False
    
    return True
