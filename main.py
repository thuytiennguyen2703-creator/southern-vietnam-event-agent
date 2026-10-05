from src.database import init_db
from src.scraper import scrape_source
from src.parser import parse_articles
from sources import SOURCES


def main():

    init_db()

    print("Database initialized successfully!")
    print()

    all_articles = []

    # ========================================================
    # SCRAPE
    # ========================================================

    for source in SOURCES:

        print("=" * 70)
        print(f"Source : {source['name']}")
        print(f"Type   : {source['type']}")

        try:
            articles = scrape_source(source)
            if source["type"] == "rss":
                print("\nRSS SAMPLE:")
                for article in articles[:10]:
                    print(
                        f"- {article['title']}"
                        f" | province={article.get('province')}"
                    )

            print(f"Found  : {len(articles)} articles")

            all_articles.extend(articles)

        except Exception as e:
            print(
                f"ERROR: {type(e).__name__}: {e}"
            )

    # ========================================================
    # PARSE
    # ========================================================

    print()
    print("=" * 70)
    print("PARSING EVENTS")
    print("=" * 70)

    events = parse_articles(all_articles)

    print(f"Total articles : {len(all_articles)}")
    print(f"Event articles : {len(events)}")

    # ========================================================
    # HIỂN THỊ
    # ========================================================

    for event in events[:20]:

        print()
        print(f"Title    : {event['title']}")
        print(f"Province : {event['province']}")
        print(f"Source   : {event['source_name']}")
        print(f"URL      : {event['url']}")


if __name__ == "__main__":
    main()