"""Interactive local configuration; never accepts secrets as CLI arguments."""
import getpass
import json
from pathlib import Path
from app.core.config import get_settings

def main():
    settings=get_settings()
    password=getpass.getpass("Mail.ru application password (hidden): ").strip()
    if not password:
        raise SystemExit("No changes: empty password")
    values={"MAIL_DELIVERY":"smtp","SMTP_HOST":"smtp.mail.ru","SMTP_PORT":"465","SMTP_SECURITY":"ssl","SMTP_USERNAME":"promtmarket@mail.ru","SMTP_FROM":"promtmarket@mail.ru","SMTP_PASSWORD":password}
    target=Path(__file__).parent/".env"
    lines=target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    lines=[line for line in lines if line.split("=",1)[0] not in values]
    lines.extend(key+"="+json.dumps(value) for key,value in values.items())
    temporary=target.with_suffix(".tmp")
    temporary.write_text("\n".join(lines)+"\n",encoding="utf-8")
    temporary.replace(target)
    print("SMTP configuration saved. Restart API and mail worker. No message was sent.")
if __name__=="__main__":main()
