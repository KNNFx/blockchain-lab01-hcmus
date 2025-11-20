from typing import Dict, Any
from .crypto_layer import blake2b_hash
from .types_tx import SignedTx
from .encoding import canonical_json

class State:
    """
    - Key must follow the format: "owner_pubkey_hex/key_name"
    - Never create bare keys (e.g., "msg")
    - Only the owner can create or modify their keys
    """
    def __init__(self, data: Dict[str, Any] = None):
        self.data: Dict[str, Any] = data or {}

    def _full_key(self, owner_pubkey: str, key: str) -> str:
        return f"{owner_pubkey}/{key}"

    def apply_tx(self, tx: SignedTx) -> bool:
        """
        Apply transaction ONLY IF:
        1. Signature is valid + context is TX:
        2. sender_pubkey is the owner of the key (strict ownership)
        """
        # 1.
        if not tx.verify():
            return False

        # 2.
        if tx.sender_pubkey_hex != tx.pubkey:
            return False

        owner = tx.sender_pubkey_hex

        suffix = f"/{tx.key}"
        for existing_full in self.data.keys():
            if existing_full.endswith(suffix):
                existing_owner = existing_full.split("/", 1)[0]
                if existing_owner != owner:
                    return False
                break

        full_key = self._full_key(owner, tx.key)
        self.data[full_key] = tx.value
        return True

    def commitment(self) -> bytes:
        sorted_items = sorted(self.data.items())
        commit_obj = {k: v for k, v in sorted_items}
        return blake2b_hash(canonical_json(commit_obj))

    def get(self, owner_pubkey: str, key: str) -> Any:
        return self.data.get(self._full_key(owner_pubkey, key))

    def copy(self) -> "State":
        import copy
        return State(copy.deepcopy(self.data))