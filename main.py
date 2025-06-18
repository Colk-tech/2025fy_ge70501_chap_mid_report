import asyncio

from analyze import main as analyze_main
from register import main as register_main
from retrieve import main as retrieve_main
from reset import main as reset_main


async def main() -> None:
    print("Initializing database...")
    await reset_main()
    print("Done.")

    print("Retrieving cases from NDL...")
    retrieve_main()
    print("Done.")

    print("Registering documents into your database...")
    await register_main()
    print("Done.")

    print("Analyzing documents...")
    await analyze_main()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
