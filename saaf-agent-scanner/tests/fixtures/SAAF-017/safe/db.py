import sqlite3

conn = sqlite3.connect("app.db")
ALLOWED_COLUMNS = {"name", "email"}


def find_user(name):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = ?", (name,))
    return cur.fetchall()


def find_doc(doc_id):
    sql = "SELECT body FROM docs WHERE id = ?"
    return conn.execute(sql, (doc_id,)).fetchone()


def delete_many(skus):
    placeholders = ",".join("?" * len(skus))
    conn.execute(f"DELETE FROM items WHERE sku IN ({placeholders})", skus)


def rename(a, b):
    conn.execute("UPDATE items SET label = :a WHERE sku = :b", {"a": a, "b": b})
