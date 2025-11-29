"""
Module Block - BlockHeader, Block, tạo block và validation
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
import binascii

from core.types_tx import SignedTx
from core.state import State
from core.crypto_layer import KeyPair, sign_struct, verify_struct, blake2b_hash
from core.encoding import canonical_json


@dataclass
class BlockHeader:
    """Block header chứa metadata"""
    height: int
    parent_hash: str
    state_hash: str
    proposer_pubkey_hex: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Block:
    """Block chứa header, transactions, và chữ ký header"""
    header: BlockHeader
    txs: List[SignedTx]
    header_signature: str
    pubkey: str
    context: str

    def block_hash(self) -> str:
        """Tính block hash từ header"""
        header_bytes = canonical_json(self.header.to_dict())
        hash_bytes = blake2b_hash(header_bytes)
        return binascii.hexlify(hash_bytes).decode()

    def verify_signature(self) -> bool:
        """Kiểm tra chữ ký header"""
        signed_header_dict = self.header.to_dict()
        signed_header_dict.update({
            "signature": self.header_signature,
            "pubkey": self.pubkey,
            "context": self.context
        })
        return verify_struct("HEADER:", signed_header_dict)

def build_block(
    parent_block: Optional[Block],
    parent_state: State,
    txs: List[SignedTx],
    keypair: KeyPair
) -> Block:
    """
    Tạo block mới từ parent block, parent state, transactions, và keypair của proposer.
    
    Args:
        parent_block: Block trước đó (None nếu là genesis block)
        parent_state: State sau khi áp dụng parent block
        txs: Danh sách các transactions đã ký
        keypair: Keypair của proposer để ký
    
    Returns:
        Block mới với header đã được proposer ký
    """
    # Xác định height và parent hash
    if parent_block is None:
        height = 0
        parent_hash = "0" * 64  # Genesis parent hash
    else:
        height = parent_block.header.height + 1
        parent_hash = parent_block.block_hash()
    
    # Áp dụng transactions để lấy state mới
    new_state = parent_state.copy()
    for tx in txs:
        new_state.apply_tx(tx)
    
    # Tính state hash
    state_commitment = new_state.commitment()
    state_hash = binascii.hexlify(state_commitment).decode()
    
    # Tạo header
    header = BlockHeader(
        height=height,
        parent_hash=parent_hash,
        state_hash=state_hash,
        proposer_pubkey_hex=keypair.pubkey()
    )
    
    # Ký header
    header_dict = header.to_dict()
    signed_header = sign_struct("HEADER:", keypair, header_dict)
    
    # Tạo block
    block = Block(
        header=header,
        txs=txs,
        header_signature=signed_header["signature"],
        pubkey=signed_header["pubkey"],
        context=signed_header["context"]
    )
    
    return block


def validate_block(
    block: Block,
    parent_block: Optional[Block],
    parent_state: State
) -> bool:
    """
    Validate block bằng cách kiểm tra:
    1. Chữ ký header hợp lệ
    2. Height đúng (parent_height + 1)
    3. Parent hash khớp
    4. State hash khớp sau khi re-execute transactions
    
    Args:
        block: Block cần validate
        parent_block: Block trước đó (None nếu là genesis)
        parent_state: State sau khi áp dụng parent block
    
    Returns:
        True nếu block hợp lệ, False nếu không
    """
    # Xác thực chữ ký header
    signed_header_dict = block.header.to_dict()
    signed_header_dict.update({
        "signature": block.header_signature,
        "pubkey": block.pubkey,
        "context": block.context
    })
    
    if not verify_struct("HEADER:", signed_header_dict):
        return False
    
    # Xác thực proposer pubkey khớp với header
    if block.header.proposer_pubkey_hex != block.pubkey:
        return False
    
    # Validate height và parent hash
    if parent_block is None:
        # Validation cho genesis block
        if block.header.height != 0:
            return False
        if block.header.parent_hash != "0" * 64:
            return False
    else:
        # Validation cho block thường
        if block.header.height != parent_block.header.height + 1:
            return False
        
        expected_parent_hash = parent_block.block_hash()
        if block.header.parent_hash != expected_parent_hash:
            return False
    
    # Re-execute transactions và xác thực state hash
    new_state = parent_state.copy()
    for tx in block.txs:
        # Áp dụng transaction (sẽ return False nếu invalid, nhưng vẫn include nó)
        new_state.apply_tx(tx)
    
    state_commitment = new_state.commitment()
    expected_state_hash = binascii.hexlify(state_commitment).decode()
    
    if block.header.state_hash != expected_state_hash:
        return False
    
    return True
