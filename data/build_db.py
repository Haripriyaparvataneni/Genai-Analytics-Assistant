"""Create data/sales.db: a small synthetic SQLite database with three tables.

  products:  product_id, name, category, unit_price
  sales:     sale_id, product_id, sale_date, quantity, unit_price
  inventory: product_id, warehouse, stock_qty, reorder_level

All rows are synthetic (seeded RNG). Run from the repo root:
    python data/build_db.py
"""
import os
import sqlite3
import numpy as np

SEED = 7
PRODUCTS = [
    (1, "Aurora Laptop 14", "Electronics", 899.99),
    (2, "Nimbus Wireless Mouse", "Electronics", 29.99),
    (3, "Terra Coffee Beans 1kg", "Grocery", 18.50),
    (4, "Vertex Standing Desk", "Furniture", 349.00),
    (5, "Pulse Bluetooth Speaker", "Electronics", 79.99),
    (6, "Drift Yoga Mat", "Sports", 34.95),
]
WAREHOUSES = ["WH-North", "WH-South"]
N_DAYS = 120


def main():
    os.makedirs("data", exist_ok=True)
    rng = np.random.default_rng(SEED)
    db_path = "data/sales.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL
        );
        CREATE TABLE sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            sale_date TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL
        );
        CREATE TABLE inventory (
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            warehouse TEXT NOT NULL,
            stock_qty INTEGER NOT NULL,
            reorder_level INTEGER NOT NULL,
            PRIMARY KEY (product_id, warehouse)
        );
    """)
    cur.executemany(
        "INSERT INTO products VALUES (?,?,?,?)", PRODUCTS
    )
    # 120 days of sales; daily quantity ~ Poisson around a per-product rate
    rates = {1: 2, 2: 25, 3: 18, 4: 1, 5: 8, 6: 6}
    dates = np.datetime64("2026-01-01") + np.arange(N_DAYS)
    rows = []
    for pid, _, _, price in PRODUCTS:
        qty = rng.poisson(rates[pid], N_DAYS)
        for d, q in zip(dates, qty):
            if q:
                rows.append((pid, str(d), int(q), price))
    rng.shuffle(rows)
    cur.executemany(
        "INSERT INTO sales (product_id, sale_date, quantity, unit_price) VALUES (?,?,?,?)",
        rows,
    )
    # inventory: two warehouses per product; make a couple of rows low/out of stock
    for pid, _, _, _ in PRODUCTS:
        for wh in WAREHOUSES:
            stock = int(rng.integers(20, 200))
            reorder = 30
            cur.execute(
                "INSERT INTO inventory VALUES (?,?,?,?)", (pid, wh, stock, reorder)
            )
    cur.execute("UPDATE inventory SET stock_qty = 0 WHERE product_id = 4 AND warehouse = 'WH-North'")
    cur.execute("UPDATE inventory SET stock_qty = 12 WHERE product_id = 6 AND warehouse = 'WH-South'")
    con.commit()
    n_sales = cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    n_inv = cur.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    con.close()
    print(f"wrote {db_path}: {len(PRODUCTS)} products, {n_sales} sales rows, {n_inv} inventory rows")


if __name__ == "__main__":
    main()
