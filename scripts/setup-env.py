"""Create private local or production environment settings without replacement."""

import argparse
import os
import re
import secrets
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--production-domain", help="Create .env.production for an owned public hostname"
)
args = parser.parse_args()
if args.production_domain and not re.fullmatch(
    r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",
    args.production_domain,
):
    parser.error("Use a lower-case public hostname without a scheme, port or path.")
root = Path(__file__).resolve().parents[1]
target = root / (".env.production" if args.production_domain else ".env")
text = (root / ".env.example").read_text()
text = text.replace("replace-with-a-local-password", secrets.token_hex(24))
text = text.replace("WEBHOOK_SIGNING_KEY=", "WEBHOOK_SIGNING_KEY=" + secrets.token_hex(32))
if args.production_domain:
    text = text.replace("APP_ENV=development", "APP_ENV=production").replace(
        "WEB_ORIGIN=http://localhost:3000",
        "WEB_ORIGIN=https://" + args.production_domain,
    )
    text += (
        "\nFLOWOPS_DOMAIN="
        + args.production_domain
        + "\nFLOWOPS_ENV_FILE=.env.production\nALLOW_PUBLIC_REGISTRATION=false\n"
    )
try:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit("An environment file already exists. It was left unchanged.") from None
with os.fdopen(descriptor, "w") as output:
    output.write(text)
print(f"Created {target.name}. Values are intentionally not displayed.")
