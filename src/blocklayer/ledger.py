"""
Module Ledger - Quản lý blocks và states theo height
"""

from typing import Optional, Tuple
from blocklayer.block import Block
from core.state import State


class Ledger:
    """
    Ledger lưu trữ blocks và states theo index là height.
    Cung cấp các phương thức để thêm blocks, lấy blocks/states, và lấy block finalized mới nhất.
    """
    
    def __init__(self):
        """Khởi tạo ledger rỗng"""
        self.blocks: dict[int, Block] = {}
        self.states: dict[int, State] = {}
    
    def add_block(self, block: Block, state_after: State) -> None:
        """
        Thêm block và state kết quả vào ledger.
        
        Args:
            block: Block cần thêm
            state_after: State sau khi áp dụng tất cả transactions trong block
        """
        height = block.header.height
        self.blocks[height] = block
        self.states[height] = state_after
    
    def get_block(self, height: int) -> Optional[Block]:
        """
        Lấy block tại height được chỉ định.
        
        Args:
            height: Chiều cao của block
        
        Returns:
            Block tại height hoặc None nếu không tìm thấy
        """
        return self.blocks.get(height)
    
    def get_state(self, height: int) -> Optional[State]:
        """
        Lấy state sau khi áp dụng block tại height được chỉ định.
        
        Args:
            height: Chiều cao của block
        
        Returns:
            State sau block tại height hoặc None nếu không tìm thấy
        """
        return self.states.get(height)
    
    def latest_finalized(self) -> Optional[Tuple[Block, State]]:
        """
        Lấy block finalized mới nhất và state của nó.
        
        Returns:
            Tuple (block, state) ở height cao nhất, hoặc None nếu ledger rỗng
        """
        if not self.blocks:
            return None
        
        max_height = max(self.blocks.keys())
        return (self.blocks[max_height], self.states[max_height])
    
    def get_height(self) -> int:
        """
        Lấy height hiện tại của ledger (height cao nhất của block).
        
        Returns:
            Block height cao nhất, hoặc -1 nếu ledger rỗng
        """
        if not self.blocks:
            return -1
        return max(self.blocks.keys())
