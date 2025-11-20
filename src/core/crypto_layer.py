import binascii
from nacl.signing import SigningKey, VerifyKey
from nacl.hash import blake2b
from nacl.encoding import RawEncoder
from .encoding import canonical_json

# Could be modified
CHAIN_ID = "blockchain-lab01-hcmus"

def blake2b_hash(data: bytes) -> bytes:
    return blake2b(data, digest_size=32, encoder=RawEncoder)

class KeyPair:
    def __init__(self, seed: bytes | None = None):
        if seed:
            self.sk = SigningKey(seed[:32])
        else:
            self.sk = SigningKey.generate()
        self.vk = self.sk.verify_key
        self.pubkey_bytes = self.vk.encode()
        self.pubkey_hex = binascii.hexlify(self.pubkey_bytes).decode()

    def pubkey(self) -> str:
        return self.pubkey_hex

def _domain_context(ctx: str) -> str:
    return f"{ctx}{CHAIN_ID}"

def sign_struct(ctx: str, keypair: KeyPair, payload: dict) -> dict:
    # ctx must be: "TX:", "HEADER:" or "VOTE:"
    context_str = _domain_context(ctx)
    to_sign = {"context": context_str, "payload": payload}
    msg_bytes = canonical_json(to_sign)
    signature = keypair.sk.sign(msg_bytes, encoder=RawEncoder).signature

    signed = payload.copy()
    signed.update({
        "signature": binascii.hexlify(signature).decode(),
        "pubkey": keypair.pubkey(),
        "context": context_str
    })
    return signed

def verify_struct(ctx: str, signed_obj: dict) -> bool:
    expected_ctx = _domain_context(ctx)
    if signed_obj.get("context") != expected_ctx:
        return False

    try:
        sig_hex = signed_obj["signature"]
        pub_hex = signed_obj["pubkey"]
        payload = {k: v for k, v in signed_obj.items()
                  if k not in ("signature", "pubkey", "context")}

        to_verify = {"context": expected_ctx, "payload": payload}
        msg_bytes = canonical_json(to_verify)
        sig_bytes = binascii.unhexlify(sig_hex)
        pub_bytes = binascii.unhexlify(pub_hex)

        VerifyKey(pub_bytes).verify(msg_bytes, sig_bytes, encoder=RawEncoder)
        return True
    except Exception:
        return False