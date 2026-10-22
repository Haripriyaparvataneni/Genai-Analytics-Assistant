# GenAI Analytics Assistant (Text-to-SQL)

Ask a question in plain English about sales/inventory data, and this little app writes the SQL for it and runs it. Something like:

```
$ python app.py "Which products have low stock?"
Question: Which products have low stock?
SQL: SELECT p.name, i.warehouse, i.stock_qty, i.reorder_level FROM inventory i
     JOIN products p ON i.product_id = p.product_id
     WHERE i.stock_qty < i.reorder_level ORDER BY i.stock_qty;
name | warehouse | stock_qty | reorder_level
Vertex Standing Desk | WH-North | 0 | 30
Drift Yoga Mat | WH-South | 12 | 30
Pulse Bluetooth Speaker | WH-North | 29 | 30
```

The database is synthetic — `data/build_db.py` creates it. Three tables: `products`, `sales` (120 days of transactions), and `inventory` (2 warehouses). Nothing here is from a real company.

## The part I cared about

I didn't want this to need an API key just to try it, so the LLM part sits behind a small interface with two backends:

- **`HeuristicLLM` (default)** — a local, pattern-based parser. Runs completely offline, no keys, no network. It handles the common analytics question shapes: totals, top/bottom N, grouping by category or warehouse, low stock, that kind of thing.
- **`BedrockLLM` (optional)** — sends the question to Claude on Amazon Bedrock for free-form questions. Only switches on if you set `USE_BEDROCK=1` and install boto3 yourself with your own AWS credentials. The default run never even imports boto3.

`schema.py` holds the database schema text that goes into the prompt, and `app.py` is the CLI — it prints the SQL first, then the results. There's an `--interactive` mode too.

If you ask something outside the local parser's patterns, it raises an error and says so, instead of making up SQL that looks right and isn't. I'd rather have it admit that than hallucinate a confident wrong answer.

## Run it

No AWS needed for the default path:

```bash
python data/build_db.py
python app.py "What is the total revenue?"
python app.py --interactive
```

`examples.md` has 8 questions I actually ran, with the SQL they produced and what came back.

With Bedrock (optional, your own AWS account):

```bash
pip install boto3        # not in requirements.txt on purpose
USE_BEDROCK=1 python app.py "Compare Q1 vs Q2 revenue by category"
```

## Files

```
data/build_db.py      # creates the synthetic SQLite database (seeded)
schema.py             # schema text used in the prompts
text_to_sql.py        # the two backends: local heuristic + optional Bedrock
app.py                # CLI: question -> SQL -> results
examples.md           # 8 example questions with real output
requirements.txt      # stdlib only for the default run
```
