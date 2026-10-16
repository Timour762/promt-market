"""Create a new admin interactively; never overwrite an existing account."""
import asyncio
import getpass
from sqlalchemy import select,or_
from app.auth.models import User,Role
from app.auth.security import password_hasher
from app.db.session import SessionFactory,engine
async def main():
    username=input("New administrator login: ").strip().lower()
    name=input("Administrator display name: ").strip()
    password=getpass.getpass("New unique password, at least 12 characters (hidden): ")
    confirmation=getpass.getpass("Repeat password (hidden): ")
    if not username or not name or len(username)>80 or len(name)>80 or len(password)<12 or len(password)>128 or password!=confirmation:
        raise SystemExit("Invalid fields or password confirmation; no changes")
    async with SessionFactory() as db:
        existing=await db.scalar(select(User.id).where(or_(User.username==username,User.email==username)))
        if existing:raise SystemExit("Account already exists; no changes")
        role=await db.scalar(select(Role).where(Role.code=="admin"))
        if role is None:raise SystemExit("Apply migrations first")
        db.add(User(username=username,name=name,password_hash=password_hasher.hash(password),role_id=role.id,status="active"))
        await db.commit()
    await engine.dispose()
    print("Administrator created; password was not printed")
if __name__=="__main__":asyncio.run(main())
