#/bin/sh

# Create the database file for a home library of books.

# Copyright 2019 Marcin Ciura
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
