import asyncio

from database import migrate


async def main() -> None:
    await migrate()


if __name__ == "__main__":
    asyncio.run(main())
