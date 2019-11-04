#!/usr/bin/python3

"""Manage a home library of books."""

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

import enum
import locale
import tkinter as tk
import tkinter.ttk as ttk
import sqlite3
import unicodedata

DATABASE_NAME = 'books.sqlite3'


class UnaccentedMap(dict):

  CHAR_REPLACEMENT = {
    ord('\N{Latin capital letter AE}'): 'AE',
    ord('\N{Latin small letter ae}'): 'ae',
    ord('\N{Latin capital letter Eth}'): 'D',
    ord('\N{Latin small letter eth}'): 'd',
    ord('\N{Latin capital letter O with stroke}'): 'OE',
    ord('\N{Latin small letter o with stroke}'): 'oe',
    ord('\N{Latin capital letter Thorn}'): 'Th',
    ord('\N{Latin small letter thorn}'): 'th',
    ord('\N{Latin small letter sharp s}'): 'ss',
    ord('\N{Latin capital letter D with stroke}'): 'Dj',
    ord('\N{Latin small letter d with stroke}'): 'dj',
    ord('\N{Latin capital letter H with stroke}'): 'H',
    ord('\N{Latin small letter h with stroke}'): 'h',
    ord('\N{Latin small letter dotless i}'): 'i',
    ord('\N{Latin small letter kra}'): 'q',
    ord('\N{Latin capital letter L with stroke}'): 'L',
    ord('\N{Latin small letter l with stroke}'): 'l',
    ord('\N{Latin capital letter Eng}'): 'Ng',
    ord('\N{Latin small letter eng}'): 'ng',
    ord('\N{Latin capital ligature OE}'): 'OE',
    ord('\N{Latin small ligature oe}'): 'oe',
    ord('\N{Latin capital letter T with stroke}'): 'Th',
    ord('\N{Latin small letter t with stroke}'): 'th',
  }

  def __missing__(self, key):
    ch = self.get(key)
    if ch is not None:
      return ch
    de = unicodedata.decomposition(chr(key))
    if de:
      try:
        ch = int(de.split(None, 1)[0], 16)
      except (IndexError, ValueError):
        ch = key
    else:
      ch = self.CHAR_REPLACEMENT.get(key, key)
    self[key] = ch
    return ch


UNACCENTED = UnaccentedMap()

@enum.unique
class Column(enum.IntEnum):
  ID = 0
  SHELF = 1
  AUTHOR = 2
  TITLE = 3
  TRANSLATOR = 4
  ORIGINAL_TITLE = 5
  BORROWED = 6
  COUNT = 7

COLUMN_NAMES = [
    'ID',
    'Shelf',
    'Author',
    'Title',
    'Translator',
    'Original title',
    'Borrowed',
]

COLUMN_ORDER = [
    Column.ID,
    Column.SHELF,
    Column.AUTHOR,
    Column.TITLE,
    Column.BORROWED,
    Column.TRANSLATOR,
    Column.ORIGINAL_TITLE,
]

CONVERSE_COLUMN_ORDER = Column.COUNT * [None]
for i, x in enumerate(COLUMN_ORDER):
  CONVERSE_COLUMN_ORDER[x] = i

DISPLAYED_COLUMNS = [COLUMN_NAMES[COLUMN_ORDER[i]] for i in range(5)]


class Application(tk.Frame):

  def __init__(self, parent, *args, **kwargs):
    self.connection = sqlite3.connect(DATABASE_NAME)
    tk.Frame.__init__(self, parent, *args, **kwargs)
    image = tk.PhotoImage(file='books.png')
    parent.tk.call('wm', 'iconphoto', parent._w, image)
    parent.rowconfigure(1, weight=1)
    parent.columnconfigure(0, weight=1)
    parent.columnconfigure(1, weight=1)
    parent.columnconfigure(2, weight=1)
    parent.columnconfigure(3, weight=1)
    self.parent = parent

    self.search_var = tk.StringVar()
    self.last_search_var = None
    self.entry = tk.Entry(parent, textvariable=self.search_var)
    self.entry.grid(row=0, column=0, columnspan=6, sticky='nswe')
    parent.bind('<Key>', self.KeyPressed)
    parent.bind('<ButtonRelease-1>', lambda e: self.entry.focus_set())

    scrollbar = tk.Scrollbar(parent)
    scrollbar.grid(row=1, rowspan=2, column=len(DISPLAYED_COLUMNS), sticky='ns')
    self.tree_view = ttk.Treeview(
        parent, columns=DISPLAYED_COLUMNS, show='headings',
        yscrollcommand=scrollbar.set)
    self.tree_view.grid(row=1, column=0, columnspan=5, sticky='nswe')
    scrollbar.config(command=self.tree_view.yview)
    self.tree_view.column(0, width=0, anchor='w', stretch=False)
    self.tree_view.column(1, width=50, anchor='w', stretch=False)
    self.tree_view.column(2, width=150, anchor='w', stretch=True)
    self.tree_view.column(3, width=300, anchor='w', stretch=True)
    self.tree_view.column(4, width=100, anchor='w', stretch=True)
    for column in DISPLAYED_COLUMNS:
      self.tree_view.heading(
          column, text=column, anchor='w',
          command=lambda column=column: self.SortBy(column, False))
    self.clicked_column = DISPLAYED_COLUMNS[Column.AUTHOR]
    self.reverse = False

    tk.Button(parent, text='Edit', command=self.Edit).grid(
        row=2, column=0, sticky='nswe')
    tk.Button(parent, text='Insert', command=self.Insert).grid(
        row=2, column=1, sticky='nswe')
    tk.Button(parent, text='Delete', command=self.Delete).grid(
        row=2, column=2, sticky='nswe')
    tk.Button(parent, text='Quit', command=parent.destroy).grid(
        row=2, column=3, sticky='nswe')

    self.SetTitle()
    self.Select()

  def SetTitle(self):
    cursor = self.connection.cursor()
    book_count = cursor.execute(
        """
        SELECT COUNT(*) FROM Books
        """).fetchone()[0]
    self.parent.title(
        'Home Library: {} book{}'.format(book_count, 's'[:book_count != 1]))

  def MakeDialog(self, name):
    dialog = tk.Toplevel(self.parent)
    dialog.title(name)
    dialog.config(padx=24, pady=24)
    dialog.transient(self.parent)
    return dialog

  @staticmethod
  def MakeEntries(dialog, item_values, enabled):
    entries = [None]
    for row in range(Column.SHELF, Column.COUNT):
      label = tk.Label(dialog, text=COLUMN_NAMES[row] + ':')
      label.grid(row=row, column=0, sticky=tk.E)
      entry = tk.Entry(dialog, width=50)
      entry.insert(0, item_values[CONVERSE_COLUMN_ORDER[row]])
      entry.grid(row=row, column=1, columnspan=2)
      if not enabled:
        entry.config(state='readonly')
      entries.append(entry)
    return entries

  @staticmethod
  def MakeButtons(dialog, button, command, red_on_left):
    if red_on_left:
      left_color, right_color = 'crimson', 'forest green'
    else:
      left_color, right_color = 'forest green', 'crimson'
    tk.Button(
        dialog,
        text='Skip',
        background=left_color,
        command=dialog.destroy).grid(row=Column.COUNT.value, column=1)
    tk.Button(
        dialog,
        text=button,
        background=right_color,
        command=command).grid(row=Column.COUNT.value, column=2)

  @staticmethod
  def BindKeys(dialog, command):
    dialog.bind('<Escape>', lambda event: dialog.destroy())
    dialog.bind('<Return>', lambda event: command())
    dialog.bind('<KP_Enter>', lambda event: command())
    
  def Finalize(self, dialog):
    self.connection.commit()
    self.last_search_var = None
    self.Select()
    dialog.destroy()

  @staticmethod
  def MakeFtsContent(content):
    return ' '.join(
        x for x in content[
            Column.AUTHOR - Column.SHELF:
            Column.ORIGINAL_TITLE + 1 - Column.SHELF]
        if x).translate(UNACCENTED)
  
  def Select(self):
    if self.search_var.get() == self.last_search_var:
      return
    self.last_search_var = self.search_var.get()
    search_pattern = ' '.join(
        [s + '*' for s in self.last_search_var.split()]).translate(UNACCENTED)
    cursor = self.connection.cursor()
    cursor.execute(
        """
        SELECT id, shelf, author, title, borrowed, translator, original_title
        FROM Books
        JOIN BooksFTS ON Books.id = BooksFTS.rowid
        WHERE BooksFTS.content MATCH ?
        """,
        (search_pattern,))
    self.tree_view.delete(*self.tree_view.get_children())
    for row in cursor.fetchall():
      columns = [x if x is not None else '' for x in row]
      self.tree_view.insert('', tk.END, values=columns)
    self.SortBy(self.clicked_column, self.reverse)

  def Insert(self):
    def InsertBook():
      for column in [Column.SHELF, Column.AUTHOR, Column.TITLE]:
        if not entries[column].get():
          return
      cursor = self.connection.cursor()
      content = [
          ' '.join(entries[i].get().strip().split())
          for i in range(Column.SHELF, Column.COUNT)]
      cursor.execute(
          """
          INSERT INTO Books(
              shelf, author, title, translator, original_title, borrowed)
          VALUES(?, ?, ?, ?, ?, ?)
          """,
          content)
      cursor.execute(
          """
          INSERT INTO BooksFTS(rowid, content) VALUES(?, ?)
          """,
          [cursor.lastrowid, self.MakeFtsContent(content)])
      self.Finalize(dialog)
      self.SetTitle()

    selected_items = self.tree_view.selection()
    dialog = self.MakeDialog('Insert a book')
    if selected_items:
      item_values = self.tree_view.item(selected_items[0], 'values')
    else:
      item_values = Column.COUNT * ['']
    entries = self.MakeEntries(dialog, item_values, True)
    self.MakeButtons(dialog, 'Insert', InsertBook, True)
    self.BindKeys(dialog, InsertBook)
    self.parent.wait_window(dialog)

  def Edit(self):
    def UpdateBook():
      for column in [Column.SHELF, Column.AUTHOR, Column.TITLE]:
        if not entries[column].get():
          return
      cursor = self.connection.cursor()
      item_id = int(item_values[Column.ID])
      content = [entries[i].get() for i in range(Column.SHELF, Column.COUNT)]
      cursor.execute(
          """
          UPDATE Books
          SET shelf = ?, author = ?, title = ?,
              translator = ?, original_title = ?, borrowed = ?
          WHERE id = ?
          """,
          content + [item_id])
      cursor.execute(
          """
          UPDATE BooksFTS SET content = ? WHERE rowid = ?
          """,
          [self.MakeFtsContent(content), item_id])
      self.Finalize(dialog)
    
    selection = self.tree_view.selection()
    if not selection:
      return
    dialog = self.MakeDialog('Edit a book')
    item_values = self.tree_view.item(selection[0], 'values')
    entries = self.MakeEntries(dialog, item_values, True)
    self.MakeButtons(dialog, 'Update', UpdateBook, True)
    self.BindKeys(dialog, UpdateBook)
    self.parent.wait_window(dialog)

  def Delete(self):
    def DeleteBook():
      cursor = self.connection.cursor()
      cursor.execute(
          """
          DELETE FROM Books WHERE id = ?;
          """,
          [item_values[Column.ID]])
      cursor.execute(
          """
          DELETE FROM BooksFTS WHERE rowid = ?
          """,
          [item_values[Column.ID]])
      self.Finalize(dialog)
      self.SetTitle()

    selection = self.tree_view.selection()
    if not selection:
      return
    dialog = self.MakeDialog('Confirm delete')
    item_values = self.tree_view.item(selection[0], 'values')
    entries = self.MakeEntries(dialog, item_values, False)
    self.MakeButtons(dialog, 'Delete', DeleteBook, False)
    self.BindKeys(dialog, DeleteBook)
    self.parent.wait_window(dialog)

  def KeyPressed(self, event):
    if event.char:
      self.Select()

  def SortBy(self, column, reverse):
    data = [
        (self.tree_view.set(child, column), child)
        for child in self.tree_view.get_children('')]
    data.sort(key=lambda it: locale.strxfrm(it[0]), reverse=reverse)
    for i, item in enumerate(data):
      self.tree_view.move(item[1], '', i)
    self.tree_view.heading(
        column,
        command=lambda column=column: self.SortBy(column, not reverse))
    self.clicked_column = column
    self.reverse = reverse
    self.entry.focus_set()


if __name__ == '__main__':
  locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')
  root = tk.Tk()
  Application(root)
  root.mainloop()
