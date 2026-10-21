import base64
import hashlib
import hmac
import secrets

ITERATIONS = 390000


def hash_password(password: str, salt: bytes | None = None, iterations: int = ITERATIONS) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(actual_salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256" or int(rounds) < 1:
            return False
        # 以雜湊當時記錄的 rounds 計算，日後調高 ITERATIONS 時舊密碼仍能登入。
        actual = hash_password(password, base64.b64decode(salt), int(rounds)).split("$", 3)[3]
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)
