import sqlite3

conn = sqlite3.connect("app.db")


def find_user(name):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cur.fetchall()


def find_doc(doc_id):
    sql = "SELECT body FROM docs WHERE id = " + doc_id
    return conn.execute(sql).fetchone()


def delete_item(item):
    conn.execute("DELETE FROM items WHERE sku = '%s'" % item)


def rename(a, b):
    conn.execute("UPDATE items SET label = '{}' WHERE sku = '{}'".format(a, b))
