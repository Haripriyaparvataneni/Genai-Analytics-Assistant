"""Expose the SQLite database schema as text for prompts / introspection."""

SCHEMA = """
Table products:
  product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, unit_price REAL
Table sales:
  sale_id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(product_id),
  sale_date TEXT (YYYY-MM-DD), quantity INTEGER, unit_price REAL
Table inventory:
  product_id INTEGER REFERENCES products(product_id), warehouse TEXT,
  stock_qty INTEGER, reorder_level INTEGER
""".strip()


def get_schema() -> str:
    """Return the schema description used in prompts."""
    return SCHEMA
