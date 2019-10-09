#/bin/sh

sqlite3 <<EOF

ATTACH DATABASE "books.sqlite3" AS B;

CREATE TABLE B.Books(
    id INTEGER PRIMARY KEY,
    shelf TEXT,
    author TEXT,
    title TEXT,
    translator TEXT,
    original_title TEXT,
    borrowed TEXT
);

CREATE VIRTUAL TABLE B.BooksFTS USING fts4(content);

EOF
