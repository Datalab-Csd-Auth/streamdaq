import pathway as pw

rows = [
    (
        1,
        {
            "author": {"id": 1, "name": "Haruki Murakami"},
            "books": [
                {"title": "Norwegian Wood", "year": 1987},
                {
                    "title": "Kafka on the Shore",
                    "year": 2002,
                    "category": "Literary Fiction",
                },
            ],
        },
    ),
    (
        2,
        {
            "author": {"id": 2, "name": "Stanisław Lem"},
            "books": [
                {"title": "Solaris", "year": 1961, "category": "Science Fiction"},
                {"title": "The Cyberiad", "year": 1967, "category": "Science Fiction"},
            ],
        },
    ),
    (
        3,
        {
            "author": {"id": 3, "name": "William Shakespeare"},
            "books": [
                {"title": "Hamlet", "year": 1603, "category": "Tragedy"},
                {"title": "Macbeth", "year": 1623, "category": "Tragedy"},
            ],
        },
    ),
]


class InputSchema(pw.Schema):
    key: int
    data: pw.Json


table = pw.debug.table_from_rows(schema=InputSchema, rows=rows)
table = table.select(
    *table,
    books=pw.this.data["books"],
    author_name=pw.unwrap(pw.this.data["author"]["name"].as_str()).str.title(),
)
table = table.flatten(pw.this.books).select(
    key=pw.this.key, books=pw.this.books, author_name=pw.this.author_name
)
pw.debug.compute_and_print(table, include_id=False)
