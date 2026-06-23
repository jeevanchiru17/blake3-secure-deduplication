import base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

class EcdsaSigner:
    @staticmethod
    def verify_signature(public_key_spki_base64: str, signature_base64: str, data: bytes) -> bool:
        """
        Verifies an ECDSA signature.
        Expects WebCrypto API format:
        - public_key: SPKI format (base64 encoded)
        - signature: Raw IEEE P1363 format (r | s) (base64 encoded)
        """
        try:
            public_key_bytes = base64.b64decode(public_key_spki_base64)
            signature_bytes = base64.b64decode(signature_base64)
            
            # WebCrypto subtle.exportKey('spki') gives DER format.
            public_key = load_der_public_key(public_key_bytes)
            
            # P-256 curve gives 64-byte signature (32 bytes r, 32 bytes s)
            if len(signature_bytes) != 64:
                print("Invalid signature length")
                return False
                
            r = int.from_bytes(signature_bytes[:32], 'big')
            s = int.from_bytes(signature_bytes[32:], 'big')
            der_signature = encode_dss_signature(r, s)
            
            public_key.verify(der_signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
