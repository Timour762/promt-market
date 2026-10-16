"""Run as a supervised application worker in the deployment environment."""
import asyncio
from app.auth.mail import deliver_mail
from app.db.session import engine
async def main():
    try:
        while True:
            await deliver_mail()
            await asyncio.sleep(30)
    finally:
        await engine.dispose()
if __name__ == "__main__":
    asyncio.run(main())
