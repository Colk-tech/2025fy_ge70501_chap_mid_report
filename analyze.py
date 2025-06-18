import asyncio

from database import get_all_words, get_associations_by_word, get_document_by_id


async def main() -> None:
    print("Retrieving all words...")

    all_words = await get_all_words()

    print(f"You have {len(all_words)} words in the database.")

    for word in all_words:
        print(f"====== {word.text} ======")

        associations_with_the_word = await get_associations_by_word(word)

        if associations_with_the_word:
            for association in associations_with_the_word:
                document = await get_document_by_id(association.document_id)

                if document is None:
                    print(f"Document with ID {document.id} not found.")
                    continue

                print(f"{document.title} ({document.id})")

        print(f"====== {len(associations_with_the_word)} docs ======")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
