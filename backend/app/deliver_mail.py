import asyncio
from app.auth.mail import deliver_local_mail
from app.db.session import engine

async def main():
    await deliver_local_mail()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
