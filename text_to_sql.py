"""Natural language -> SQL for the sales/inventory SQLite database.

Architecture: a pluggable LLM interface. The default is a local,
pattern-based heuristic model that runs fully offline (no API keys, no
network). An Amazon Bedrock hook is available as an OPTIONAL alternative:
set USE_BEDROCK=1 and install boto3 yourself. The default path never
imports boto3 and never touches AWS.
"""
import os
import re


class BaseLLM:
    """Interface every question->SQL backend must implement."""

    def generate_sql(self, question: str, schema: str) -> str:
        raise NotImplementedError


class HeuristicLLM(BaseLLM):
    """Local offline model: pattern-based question parsing.

    Handles common analytics question shapes (totals, top-N, low stock,
    per-product lookups). Raises ValueError when a question matches no
    known pattern instead of guessing a wrong query.
    """

    def __init__(self):
        self.rules = [
            (re.compile(r"\btotal\s+revenue\b"), self._total_revenue),
            (re.compile(r"\baverage\s+daily\s+revenue\b"), self._avg_daily_revenue),
            (re.compile(r"\btop\s+(?P<n>\d+)\s+products?\s+by\s+(revenue|sales)\b"), self._top_products),
            (re.compile(r"\bbest-?selling\b"), self._top_products),
            (re.compile(r"\blow\s+(stock|inventory)\b"), self._low_stock),
            (re.compile(r"\breorder\b"), self._low_stock),
            (re.compile(r"\bout\s+of\s+stock\b"), self._out_of_stock),
            (re.compile(r"\bhow\s+many\s+units?\s+of\b"), self._units_of_product),
            (re.compile(r"\bunits?\s+sold\b"), self._top_products),
            (re.compile(r"\blist\s+(all\s+)?products\b"), self._list_products),
            (re.compile(r"\bproducts?\s+by\s+category\b"), self._products_by_category),
            (re.compile(r"\binventory\s+(levels?|by\s+warehouse)\b"), self._inventory_by_warehouse),
            (re.compile(r"\brevenue\s+by\s+category\b"), self._revenue_by_category),
        ]

    # -- entry point ------------------------------------------------------
    def generate_sql(self, question: str, schema: str) -> str:
        q = question.lower()
        for pattern, handler in self.rules:
            m = pattern.search(q)
            if m:
                return handler(q, m)
        raise ValueError(
            f"Cannot parse question with the local heuristic model: {question!r}. "
            "Try an OPTIONAL Bedrock backend (USE_BEDROCK=1) for free-form questions."
        )

    # -- handlers ---------------------------------------------------------
    def _total_revenue(self, q, m):
        return "SELECT ROUND(SUM(quantity * unit_price), 2) AS total_revenue FROM sales;"

    def _avg_daily_revenue(self, q, m):
        return (
            "SELECT ROUND(AVG(daily_revenue), 2) AS avg_daily_revenue FROM ("
            "SELECT sale_date, SUM(quantity * unit_price) AS daily_revenue "
            "FROM sales GROUP BY sale_date);"
        )

    def _top_products(self, q, m):
        limit = int(m.group("n")) if m.groupdict().get("n") else None
        if limit is None:  # handle "... by units? Top 3" word order
            tail = re.search(r"\btop\s+(\d+)\b", q)
            limit = int(tail.group(1)) if tail else 5
        if "units" in q or "unit" in q:
            select, order = "SUM(s.quantity) AS units_sold", "units_sold"
        else:
            select, order = "ROUND(SUM(s.quantity * s.unit_price), 2) AS revenue", "revenue"
        return (
            f"SELECT p.name, {select} FROM sales s "
            f"JOIN products p ON s.product_id = p.product_id "
            f"GROUP BY p.name ORDER BY {order} DESC LIMIT {limit};"
        )

    def _low_stock(self, q, m):
        return (
            "SELECT p.name, i.warehouse, i.stock_qty, i.reorder_level "
            "FROM inventory i JOIN products p ON i.product_id = p.product_id "
            "WHERE i.stock_qty < i.reorder_level ORDER BY i.stock_qty;"
        )

    def _out_of_stock(self, q, m):
        return (
            "SELECT p.name, i.warehouse FROM inventory i "
            "JOIN products p ON i.product_id = p.product_id "
            "WHERE i.stock_qty = 0;"
        )

    def _units_of_product(self, q, m):
        name = self._extract_product_name(q)
        return (
            f"SELECT p.name, SUM(s.quantity) AS units_sold FROM sales s "
            f"JOIN products p ON s.product_id = p.product_id "
            f"WHERE LOWER(p.name) LIKE '%{name}%' GROUP BY p.name;"
        )

    def _list_products(self, q, m):
        return "SELECT name, category, unit_price FROM products ORDER BY name;"

    def _products_by_category(self, q, m):
        return (
            "SELECT category, COUNT(*) AS num_products FROM products "
            "GROUP BY category ORDER BY num_products DESC;"
        )

    def _inventory_by_warehouse(self, q, m):
        return (
            "SELECT warehouse, SUM(stock_qty) AS total_units FROM inventory "
            "GROUP BY warehouse;"
        )

    def _revenue_by_category(self, q, m):
        return (
            "SELECT p.category, ROUND(SUM(s.quantity * s.unit_price), 2) AS revenue "
            "FROM sales s JOIN products p ON s.product_id = p.product_id "
            "GROUP BY p.category ORDER BY revenue DESC;"
        )

    # -- helpers ----------------------------------------------------------
    def _extract_product_name(self, q: str) -> str:
        known = ["laptop", "mouse", "coffee", "desk", "speaker", "yoga", "mat"]
        for token in known:
            if token in q:
                return token
        raise ValueError(f"Could not identify a product name in: {q!r}")


class BedrockLLM(BaseLLM):
    """OPTIONAL Amazon Bedrock backend (e.g., Claude via Bedrock).

    Enabled only when USE_BEDROCK=1 is set. Requires boto3 and AWS
    credentials configured in the environment; neither is needed otherwise.
    """

    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
                 region: str = "us-east-1"):
        try:
            import boto3  # lazy import: optional dependency
        except ImportError as exc:
            raise RuntimeError(
                "BedrockLLM requires boto3, which is not installed. "
                "Install it with: pip install boto3"
            ) from exc
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def generate_sql(self, question: str, schema: str) -> str:
        import json

        prompt = (
            "You are a text-to-SQL assistant. Given the SQLite schema below, "
            "write a single SQLite query answering the question. "
            "Return ONLY the SQL, no explanation.\n\n"
            f"Schema:\n{schema}\n\nQuestion: {question}\nSQL:"
        )
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = self.client.invoke_model(
            modelId=self.model_id, body=json.dumps(body)
        )
        text = json.loads(resp["body"].read())["content"][0]["text"].strip()
        return text if text.endswith(";") else text + ";"


def get_llm() -> BaseLLM:
    """Return the configured backend: Bedrock if USE_BEDROCK=1, else local."""
    if os.environ.get("USE_BEDROCK") == "1":
        return BedrockLLM()
    return HeuristicLLM()
