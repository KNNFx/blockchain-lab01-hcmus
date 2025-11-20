from dataclasses import dataclass, asdict
from typing import Any
from .crypto_layer import KeyPair, sign_struct, verify_struct

@dataclass
class TxBody:
    sender_pubkey_hex: str
    key: str
    value: Any

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SignedTx:
    sender_pubkey_hex: str
    key: str
    value: Any
    signature: str
    pubkey: str
    context: str

    @staticmethod
    def create(body: TxBody, keypair: KeyPair) -> "SignedTx":
        payload = body.to_dict()
        signed_dict = sign_struct("TX:", keypair, payload)
        return SignedTx(**signed_dict)

    def verify(self) -> bool:
        return verify_struct("TX:", asdict(self))