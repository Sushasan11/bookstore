"""Seed script for genres and books.

Populates the database with sample genres and books. Run with:
    poetry run python scripts/seed_books.py
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select


GENRES = [
    "Fiction",
    "Science Fiction",
    "Fantasy",
    "Mystery",
    "Non-Fiction",
    "Biography",
    "History",
    "Science",
    "Self-Help",
    "Romance",
]

BOOKS = [
    # Fiction
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "price": Decimal("12.99"),
        "isbn": "978-0-7432-7356-5",
        "description": "A story of the mysteriously wealthy Jay Gatsby and his love for Daisy Buchanan, set in the Jazz Age on Long Island.",
        "publish_date": date(1925, 4, 10),
        "stock_quantity": 25,
        "genre": "Fiction",
    },
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "price": Decimal("14.99"),
        "isbn": "978-0-06-112008-4",
        "description": "The story of racial injustice and the loss of innocence in the American South, seen through the eyes of young Scout Finch.",
        "publish_date": date(1960, 7, 11),
        "stock_quantity": 30,
        "genre": "Fiction",
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "price": Decimal("13.99"),
        "isbn": "978-0-451-52493-5",
        "description": "A dystopian novel set in a totalitarian society ruled by Big Brother, exploring themes of surveillance and control.",
        "publish_date": date(1949, 6, 8),
        "stock_quantity": 20,
        "genre": "Fiction",
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "price": Decimal("11.99"),
        "isbn": "978-0-14-143951-8",
        "description": "The tale of Elizabeth Bennet and Mr. Darcy navigating manners, morality, and marriage in Regency-era England.",
        "publish_date": date(1813, 1, 28),
        "stock_quantity": 18,
        "genre": "Fiction",
    },
    {
        "title": "The Catcher in the Rye",
        "author": "J.D. Salinger",
        "price": Decimal("10.99"),
        "isbn": "978-0-316-76948-0",
        "description": "Holden Caulfield narrates his experiences in New York City after being expelled from prep school.",
        "publish_date": date(1951, 7, 16),
        "stock_quantity": 15,
        "genre": "Fiction",
    },
    # Science Fiction
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "price": Decimal("16.99"),
        "isbn": "978-0-441-17271-9",
        "description": "Set on the desert planet Arrakis, this epic follows Paul Atreides as he navigates politics, religion, and ecology.",
        "publish_date": date(1965, 8, 1),
        "stock_quantity": 22,
        "genre": "Science Fiction",
    },
    {
        "title": "Neuromancer",
        "author": "William Gibson",
        "price": Decimal("14.99"),
        "isbn": "978-0-441-56956-4",
        "description": "A washed-up hacker is hired for one last job in this groundbreaking cyberpunk novel.",
        "publish_date": date(1984, 7, 1),
        "stock_quantity": 12,
        "genre": "Science Fiction",
    },
    {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "price": Decimal("15.99"),
        "isbn": "978-0-441-47812-5",
        "description": "An envoy from Earth visits the planet Gethen, whose inhabitants can change gender, exploring themes of identity.",
        "publish_date": date(1969, 3, 1),
        "stock_quantity": 10,
        "genre": "Science Fiction",
    },
    # Fantasy
    {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "price": Decimal("14.99"),
        "isbn": "978-0-547-92822-7",
        "description": "Bilbo Baggins embarks on an unexpected journey with a group of dwarves to reclaim their homeland from a dragon.",
        "publish_date": date(1937, 9, 21),
        "stock_quantity": 35,
        "genre": "Fantasy",
    },
    {
        "title": "A Game of Thrones",
        "author": "George R.R. Martin",
        "price": Decimal("18.99"),
        "isbn": "978-0-553-10354-0",
        "description": "Noble families wage war for control of the Iron Throne in the fictional continents of Westeros and Essos.",
        "publish_date": date(1996, 8, 1),
        "stock_quantity": 28,
        "genre": "Fantasy",
    },
    {
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "price": Decimal("15.99"),
        "isbn": "978-0-7564-0407-9",
        "description": "Kvothe, a legendary figure, tells his own story from his childhood in a troupe of traveling players to his years at university.",
        "publish_date": date(2007, 3, 27),
        "stock_quantity": 14,
        "genre": "Fantasy",
    },
    # Mystery
    {
        "title": "The Girl with the Dragon Tattoo",
        "author": "Stieg Larsson",
        "price": Decimal("15.99"),
        "isbn": "978-0-307-45440-0",
        "description": "A journalist and a young computer hacker investigate a wealthy family's dark secrets spanning decades.",
        "publish_date": date(2005, 8, 1),
        "stock_quantity": 16,
        "genre": "Mystery",
    },
    {
        "title": "Gone Girl",
        "author": "Gillian Flynn",
        "price": Decimal("14.99"),
        "isbn": "978-0-307-58836-4",
        "description": "On the morning of their fifth wedding anniversary, Amy Dunne disappears, and suspicion falls on her husband Nick.",
        "publish_date": date(2012, 6, 5),
        "stock_quantity": 20,
        "genre": "Mystery",
    },
    {
        "title": "And Then There Were None",
        "author": "Agatha Christie",
        "price": Decimal("12.99"),
        "isbn": "978-0-06-207348-8",
        "description": "Ten strangers are lured to an island, where they are accused of past crimes and begin to die one by one.",
        "publish_date": date(1939, 11, 6),
        "stock_quantity": 22,
        "genre": "Mystery",
    },
    # Non-Fiction
    {
        "title": "Sapiens: A Brief History of Humankind",
        "author": "Yuval Noah Harari",
        "price": Decimal("19.99"),
        "isbn": "978-0-06-231609-7",
        "description": "A sweeping narrative of human history from the Stone Age to the present, exploring how Homo sapiens came to dominate Earth.",
        "publish_date": date(2011, 1, 1),
        "stock_quantity": 30,
        "genre": "Non-Fiction",
    },
    {
        "title": "Thinking, Fast and Slow",
        "author": "Daniel Kahneman",
        "price": Decimal("17.99"),
        "isbn": "978-0-374-27563-1",
        "description": "Nobel laureate Daniel Kahneman explores the two systems that drive the way we think: fast intuition and slow deliberation.",
        "publish_date": date(2011, 10, 25),
        "stock_quantity": 18,
        "genre": "Non-Fiction",
    },
    # Biography
    {
        "title": "Steve Jobs",
        "author": "Walter Isaacson",
        "price": Decimal("19.99"),
        "isbn": "978-1-4516-4853-9",
        "description": "The authorized biography of the Apple co-founder, based on more than forty interviews with Jobs.",
        "publish_date": date(2011, 10, 24),
        "stock_quantity": 14,
        "genre": "Biography",
    },
    {
        "title": "Becoming",
        "author": "Michelle Obama",
        "price": Decimal("18.99"),
        "isbn": "978-1-5247-6313-8",
        "description": "The former First Lady chronicles her journey from the South Side of Chicago to the White House.",
        "publish_date": date(2018, 11, 13),
        "stock_quantity": 25,
        "genre": "Biography",
    },
    # History
    {
        "title": "Guns, Germs, and Steel",
        "author": "Jared Diamond",
        "price": Decimal("18.99"),
        "isbn": "978-0-393-31755-8",
        "description": "Why did history unfold differently on different continents? Diamond explores environmental and geographical factors.",
        "publish_date": date(1997, 3, 1),
        "stock_quantity": 12,
        "genre": "History",
    },
    {
        "title": "The Silk Roads",
        "author": "Peter Frankopan",
        "price": Decimal("17.99"),
        "isbn": "978-1-101-91237-9",
        "description": "A new history of the world told through the ancient trade routes that connected East and West.",
        "publish_date": date(2015, 3, 5),
        "stock_quantity": 10,
        "genre": "History",
    },
    # Science
    {
        "title": "A Brief History of Time",
        "author": "Stephen Hawking",
        "price": Decimal("16.99"),
        "isbn": "978-0-553-38016-3",
        "description": "Hawking explores fundamental questions about the universe: where it came from, where it's going, and how it will end.",
        "publish_date": date(1988, 4, 1),
        "stock_quantity": 20,
        "genre": "Science",
    },
    {
        "title": "The Selfish Gene",
        "author": "Richard Dawkins",
        "price": Decimal("15.99"),
        "isbn": "978-0-19-857519-1",
        "description": "Dawkins argues that evolution is best understood from the perspective of the gene, introducing the concept of the meme.",
        "publish_date": date(1976, 1, 1),
        "stock_quantity": 11,
        "genre": "Science",
    },
    # Self-Help
    {
        "title": "Atomic Habits",
        "author": "James Clear",
        "price": Decimal("16.99"),
        "isbn": "978-0-7352-1129-2",
        "description": "A practical guide to building good habits and breaking bad ones, backed by scientific research.",
        "publish_date": date(2018, 10, 16),
        "stock_quantity": 40,
        "genre": "Self-Help",
    },
    {
        "title": "The 7 Habits of Highly Effective People",
        "author": "Stephen R. Covey",
        "price": Decimal("15.99"),
        "isbn": "978-1-9821-3713-5",
        "description": "A principle-centered approach for solving personal and professional problems through character development.",
        "publish_date": date(1989, 8, 15),
        "stock_quantity": 18,
        "genre": "Self-Help",
    },
    # Romance
    {
        "title": "The Notebook",
        "author": "Nicholas Sparks",
        "price": Decimal("13.99"),
        "isbn": "978-1-5387-6783-0",
        "description": "An elderly man reads a notebook to a woman with Alzheimer's, recounting their epic love story from decades ago.",
        "publish_date": date(1996, 10, 1),
        "stock_quantity": 16,
        "genre": "Romance",
    },
    {
        "title": "Outlander",
        "author": "Diana Gabaldon",
        "price": Decimal("17.99"),
        "isbn": "978-0-440-21256-0",
        "description": "A WWII nurse is mysteriously transported back to 18th-century Scotland, where she meets a Highland warrior.",
        "publish_date": date(1991, 6, 1),
        "stock_quantity": 14,
        "genre": "Romance",
    },
    # --- Additional books ---
    # Fiction
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "price": Decimal("13.99"),
        "isbn": "978-0-06-085052-4",
        "description": "A futuristic World State where citizens are genetically modified and socially conditioned to serve a ruling order.",
        "publish_date": date(1932, 1, 1),
        "stock_quantity": 22,
        "genre": "Fiction",
    },
    {
        "title": "One Hundred Years of Solitude",
        "author": "Gabriel Garcia Marquez",
        "price": Decimal("15.99"),
        "isbn": "978-0-06-088328-7",
        "description": "The multi-generational story of the Buendia family in the fictional town of Macondo, blending reality and magic.",
        "publish_date": date(1967, 5, 30),
        "stock_quantity": 14,
        "genre": "Fiction",
    },
    {
        "title": "The Road",
        "author": "Cormac McCarthy",
        "price": Decimal("14.99"),
        "isbn": "978-0-307-38789-9",
        "description": "A father and son journey through a post-apocalyptic landscape, struggling to survive while holding onto hope.",
        "publish_date": date(2006, 9, 26),
        "stock_quantity": 16,
        "genre": "Fiction",
    },
    {
        "title": "Slaughterhouse-Five",
        "author": "Kurt Vonnegut",
        "price": Decimal("13.99"),
        "isbn": "978-0-385-33348-1",
        "description": "Billy Pilgrim becomes unstuck in time, traveling between his life as a WWII prisoner of war and his abduction by aliens.",
        "publish_date": date(1969, 3, 31),
        "stock_quantity": 12,
        "genre": "Fiction",
    },
    # Science Fiction
    {
        "title": "Foundation",
        "author": "Isaac Asimov",
        "price": Decimal("15.99"),
        "isbn": "978-0-553-29335-7",
        "description": "A mathematician develops a science to predict the future of civilization and establishes a foundation to preserve knowledge.",
        "publish_date": date(1951, 5, 1),
        "stock_quantity": 18,
        "genre": "Science Fiction",
    },
    {
        "title": "Ender's Game",
        "author": "Orson Scott Card",
        "price": Decimal("14.99"),
        "isbn": "978-0-312-93208-4",
        "description": "A gifted child is sent to a military academy in space to prepare for an alien invasion threatening Earth.",
        "publish_date": date(1985, 1, 15),
        "stock_quantity": 20,
        "genre": "Science Fiction",
    },
    # Fantasy
    {
        "title": "The Fellowship of the Ring",
        "author": "J.R.R. Tolkien",
        "price": Decimal("16.99"),
        "isbn": "978-0-547-92821-0",
        "description": "Frodo Baggins inherits the One Ring and must journey to Mount Doom to destroy it before the Dark Lord Sauron reclaims it.",
        "publish_date": date(1954, 7, 29),
        "stock_quantity": 30,
        "genre": "Fantasy",
    },
    {
        "title": "Harry Potter and the Sorcerer's Stone",
        "author": "J.K. Rowling",
        "price": Decimal("14.99"),
        "isbn": "978-0-590-35340-3",
        "description": "An orphaned boy discovers he is a wizard and begins his education at Hogwarts School of Witchcraft and Wizardry.",
        "publish_date": date(1997, 6, 26),
        "stock_quantity": 45,
        "genre": "Fantasy",
    },
    # Mystery
    {
        "title": "The Da Vinci Code",
        "author": "Dan Brown",
        "price": Decimal("15.99"),
        "isbn": "978-0-307-47427-9",
        "description": "A symbologist uncovers a trail of clues hidden in the works of Leonardo da Vinci that lead to a centuries-old secret.",
        "publish_date": date(2003, 3, 18),
        "stock_quantity": 24,
        "genre": "Mystery",
    },
    {
        "title": "The Silence of the Lambs",
        "author": "Thomas Harris",
        "price": Decimal("14.99"),
        "isbn": "978-0-312-92458-4",
        "description": "FBI trainee Clarice Starling seeks the help of imprisoned cannibalistic serial killer Hannibal Lecter to catch another killer.",
        "publish_date": date(1988, 5, 1),
        "stock_quantity": 15,
        "genre": "Mystery",
    },
    # Non-Fiction
    {
        "title": "Educated",
        "author": "Tara Westover",
        "price": Decimal("16.99"),
        "isbn": "978-0-399-59050-4",
        "description": "A memoir of a woman who grows up in a survivalist family in Idaho and goes on to earn a PhD from Cambridge University.",
        "publish_date": date(2018, 2, 20),
        "stock_quantity": 22,
        "genre": "Non-Fiction",
    },
    {
        "title": "Freakonomics",
        "author": "Steven D. Levitt",
        "price": Decimal("15.99"),
        "isbn": "978-0-06-073132-8",
        "description": "An economist explores the hidden side of everything, from cheating teachers to the economics of drug dealing.",
        "publish_date": date(2005, 4, 12),
        "stock_quantity": 16,
        "genre": "Non-Fiction",
    },
    # Biography
    {
        "title": "The Diary of a Young Girl",
        "author": "Anne Frank",
        "price": Decimal("12.99"),
        "isbn": "978-0-553-29698-3",
        "description": "The writings of a Jewish girl hiding from the Nazis in Amsterdam during World War II.",
        "publish_date": date(1947, 6, 25),
        "stock_quantity": 20,
        "genre": "Biography",
    },
    {
        "title": "Long Walk to Freedom",
        "author": "Nelson Mandela",
        "price": Decimal("18.99"),
        "isbn": "978-0-316-54818-2",
        "description": "The autobiography of South Africa's first Black president, chronicling his struggle against apartheid.",
        "publish_date": date(1994, 12, 1),
        "stock_quantity": 12,
        "genre": "Biography",
    },
    # History
    {
        "title": "A People's History of the United States",
        "author": "Howard Zinn",
        "price": Decimal("18.99"),
        "isbn": "978-0-06-083865-2",
        "description": "American history told from the perspective of common people rather than political and economic elites.",
        "publish_date": date(1980, 1, 1),
        "stock_quantity": 14,
        "genre": "History",
    },
    {
        "title": "The Art of War",
        "author": "Sun Tzu",
        "price": Decimal("9.99"),
        "isbn": "978-1-59030-225-9",
        "description": "An ancient Chinese military treatise on strategy and tactics that remains influential in business and warfare.",
        "publish_date": date(500, 1, 1),
        "stock_quantity": 25,
        "genre": "History",
    },
    # Science
    {
        "title": "Cosmos",
        "author": "Carl Sagan",
        "price": Decimal("16.99"),
        "isbn": "978-0-345-53943-4",
        "description": "A sweeping exploration of the universe, from the Big Bang to the search for extraterrestrial intelligence.",
        "publish_date": date(1980, 10, 12),
        "stock_quantity": 18,
        "genre": "Science",
    },
    {
        "title": "The Origin of Species",
        "author": "Charles Darwin",
        "price": Decimal("12.99"),
        "isbn": "978-0-451-52906-0",
        "description": "Darwin's groundbreaking work on the theory of evolution by natural selection that transformed biology.",
        "publish_date": date(1859, 11, 24),
        "stock_quantity": 10,
        "genre": "Science",
    },
    # Self-Help
    {
        "title": "How to Win Friends and Influence People",
        "author": "Dale Carnegie",
        "price": Decimal("14.99"),
        "isbn": "978-0-671-02703-2",
        "description": "Timeless advice on building relationships, winning people over, and influencing others effectively.",
        "publish_date": date(1936, 10, 1),
        "stock_quantity": 22,
        "genre": "Self-Help",
    },
    {
        "title": "The Power of Now",
        "author": "Eckhart Tolle",
        "price": Decimal("15.99"),
        "isbn": "978-1-57731-480-6",
        "description": "A guide to spiritual enlightenment that emphasizes the importance of living in the present moment.",
        "publish_date": date(1997, 1, 1),
        "stock_quantity": 16,
        "genre": "Self-Help",
    },
    # Romance
    {
        "title": "The Time Traveler's Wife",
        "author": "Audrey Niffenegger",
        "price": Decimal("14.99"),
        "isbn": "978-0-15-602943-8",
        "description": "A love story about a man with a genetic disorder that causes him to time travel unpredictably, and the woman who loves him.",
        "publish_date": date(2003, 9, 1),
        "stock_quantity": 12,
        "genre": "Romance",
    },
    {
        "title": "Me Before You",
        "author": "Jojo Moyes",
        "price": Decimal("15.99"),
        "isbn": "978-0-14-312443-4",
        "description": "A young woman becomes a caregiver for a paralyzed man, and their unexpected bond transforms both their lives.",
        "publish_date": date(2012, 1, 5),
        "stock_quantity": 18,
        "genre": "Romance",
    },
]


async def seed_books() -> None:
    from app.books.models import Book, Genre
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # Upsert genres
        genre_map: dict[str, int] = {}
        for name in GENRES:
            result = await session.execute(select(Genre).where(Genre.name == name))
            genre = result.scalar_one_or_none()
            if genre is None:
                genre = Genre(name=name)
                session.add(genre)
                await session.flush()
                print(f"  Created genre: {name} (id={genre.id})")
            else:
                print(f"  Genre exists: {name} (id={genre.id})")
            genre_map[name] = genre.id

        # Upsert books (by ISBN)
        created = 0
        skipped = 0
        for data in BOOKS:
            genre_name = data.pop("genre")
            isbn = data.get("isbn")

            existing = None
            if isbn:
                result = await session.execute(select(Book).where(Book.isbn == isbn))
                existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                print(f"  Skipped (exists): {data['title']}")
            else:
                book = Book(**data, genre_id=genre_map[genre_name])
                session.add(book)
                created += 1
                print(f"  Created book: {data['title']}")

            # Restore genre key for re-runnability
            data["genre"] = genre_name

        await session.commit()
        print(f"\nDone: {created} books created, {skipped} skipped (already existed)")


def main() -> None:
    print("=== Bookstore Book Seed ===\n")
    print("Seeding genres...")
    asyncio.run(seed_books())


if __name__ == "__main__":
    main()
