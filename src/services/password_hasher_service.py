from pwdlib import PasswordHash as PH
from pwdlib.hashers.bcrypt import BcryptHasher


class PasswordHasherService:
    _ph = PH((BcryptHasher(),))

    def hash(self, password: str) -> str:
        return self._ph.hash(password)

    def verify(self, password: str, hash: str) -> bool:
        return self._ph.verify(password, hash)
