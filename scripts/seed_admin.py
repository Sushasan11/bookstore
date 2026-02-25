"""Admin seed script.

Creates the first admin user in the database. Run with:
    poetry run python scripts/seed_admin.py
"""

import asyncio
import sys

from sqlalchemy.exc import IntegrityError


async def create_admin(email: str, password: str) -> None:
    """Create a user with admin role."""
    from app.core.security import hash_password
    from app.db.session import AsyncSessionLocal
    from app.users.repository import UserRepository

    hashed = await hash_password(password)

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)

        existing = await repo.get_by_email(email)
        if existing:
            print(
                f"Error: user with email '{email}' already exists "
                f"(id={existing.id}, role={existing.role.value})"
            )
            sys.exit(1)

        try:
            user = await repo.create(email=email, hashed_password=hashed)
            await repo.set_role_admin(user.id)
            await session.commit()
            print(f"Admin created: {email} (id={user.id})")
        except IntegrityError:
            await session.rollback()
            print(f"Error: email '{email}' is already taken")
            sys.exit(1)


def main() -> None:
    import getpass

    print("=== Bookstore Admin Seed ===")
    email = input("Admin email: ").strip()
    if not email:
        print("Error: email is required")
        sys.exit(1)

    password = getpass.getpass("Admin password: ")
    if len(password) < 8:
        print("Error: password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(create_admin(email, password))


if __name__ == "__main__":
    main()
