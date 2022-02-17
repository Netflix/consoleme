import os

from nacl.encoding import Base64Encoder, RawEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


class Crypto:
    def __init__(self) -> None:
        self.load_secrets()

    def load_secrets(self) -> None:
        if not config.get("ed25519.signing_key"):
            # Generating keys on demand. This is useful for unit tests
            self.signing_key = SigningKey.generate()
            self.verifying_key = self.signing_key.verify_key
            return

        signing_key_file = os.path.expanduser(config.get("ed25519.signing_key"))
        try:
            with open(signing_key_file, "rb") as signing_file:
                signing_key_bytes: bytes = signing_file.read()
        except FileNotFoundError:
            msg = "Unable to load signing key"
            log.error(msg, exc_info=True)
            raise Exception(msg)
        self.signing_key = SigningKey(signing_key_bytes, encoder=RawEncoder)
        verifying_key_file = config.get("ed25519.verifying_key")
        try:
            with open(verifying_key_file, "rb") as verifying_file:
                verifying_key_bytes: bytes = verifying_file.read()
        except FileNotFoundError:
            msg = "Unable to load verifying key"
            log.error(msg, exc_info=True)
            raise Exception(msg)
        self.verifying_key = VerifyKey(verifying_key_bytes)

    def sign(self, s: str) -> bytes:
        return self.signing_key.sign(s.encode(), encoder=Base64Encoder)

    def verify(self, s, sig):
        try:
            if not s:
                return False
            self.verifying_key.verify(sig, s.encode(), encoding="base64")
            return True
        except BadSignatureError:
            stats.count("verify.bad_sig")
            log.error("Bad signature", exc_info=True)
            return False
