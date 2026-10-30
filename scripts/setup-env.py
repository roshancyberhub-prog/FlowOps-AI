"""Create a private local environment file without replacing an existing one."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
password = secrets.token_hex(24)
text = (root / ".env.example").read_text()
text = text.replace("replace-with-a-local-password", password)
text = text.replace(
    "WEBHOOK_SIGNING_KEY=", "WEBHOOK_SIGNING_KEY=" + secrets.token_hex(32)
)
try:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit(
        "An environment file already exists. It was left unchanged."
    ) from None
with os.fdopen(descriptor, "w") as output:
    output.write(text)
print("Created local environment settings. Values are intentionally not displayed.")
