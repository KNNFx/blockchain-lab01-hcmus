import canonicaljson

def canonical_json(obj) -> bytes:
    return canonicaljson.encode_canonical_json(obj)