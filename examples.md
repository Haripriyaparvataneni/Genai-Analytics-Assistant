# Example Questions

All examples below were run against the seeded synthetic database built by
`data/build_db.py` (`seed = 7`, 120 days of sales). Outputs are real.

## 1. Total revenue

**Q:** What is the total revenue?

**SQL:**
```sql
SELECT ROUND(SUM(quantity * unit_price), 2) AS total_revenue FROM sales;
```

**Result:**
```
total_revenue
477176.53
```

## 2. Top products by revenue

**Q:** Show me the top 5 products by revenue

**SQL:**
```sql
SELECT p.name, ROUND(SUM(s.quantity * s.unit_price), 2) AS revenue
FROM sales s JOIN products p ON s.product_id = p.product_id
GROUP BY p.name ORDER BY revenue DESC LIMIT 5;
```

**Result:**
```
Aurora Laptop 14 | 197997.8
Nimbus Wireless Mouse | 92759.07
Pulse Bluetooth Speaker | 80309.96
Vertex Standing Desk | 40484.0
Terra Coffee Beans 1kg | 39553.0
```

## 3. Low stock (below reorder level)

**Q:** Which products have low stock?

**SQL:**
```sql
SELECT p.name, i.warehouse, i.stock_qty, i.reorder_level
FROM inventory i JOIN products p ON i.product_id = p.product_id
WHERE i.stock_qty < i.reorder_level ORDER BY i.stock_qty;
```

**Result:**
```
Vertex Standing Desk | WH-North | 0 | 30
Drift Yoga Mat | WH-South | 12 | 30
Pulse Bluetooth Speaker | WH-North | 29 | 30
```

## 4. Units sold for one product

**Q:** How many units of the laptop were sold?

**SQL:**
```sql
SELECT p.name, SUM(s.quantity) AS units_sold FROM sales s
JOIN products p ON s.product_id = p.product_id
WHERE LOWER(p.name) LIKE '%laptop%' GROUP BY p.name;
```

**Result:**
```
Aurora Laptop 14 | 220
```

## 5. Average daily revenue

**Q:** What is the average daily revenue?

**SQL:**
```sql
SELECT ROUND(AVG(daily_revenue), 2) AS avg_daily_revenue FROM (
  SELECT sale_date, SUM(quantity * unit_price) AS daily_revenue
  FROM sales GROUP BY sale_date);
```

**Result:**
```
avg_daily_revenue
3976.47
```

## 6. Revenue by category

**Q:** Show revenue by category

**SQL:**
```sql
SELECT p.category, ROUND(SUM(s.quantity * s.unit_price), 2) AS revenue
FROM sales s JOIN products p ON s.product_id = p.product_id
GROUP BY p.category ORDER BY revenue DESC;
```

**Result:**
```
Electronics | 371066.83
Furniture | 40484.0
Grocery | 39553.0
Sports | 26072.7
```

## 7. Out-of-stock products

**Q:** Which products are out of stock?

**SQL:**
```sql
SELECT p.name, i.warehouse FROM inventory i
JOIN products p ON i.product_id = p.product_id
WHERE i.stock_qty = 0;
```

**Result:**
```
Vertex Standing Desk | WH-North
```

## 8. Best sellers by units

**Q:** What are the best-selling products by units? Top 3

**SQL:**
```sql
SELECT p.name, SUM(s.quantity) AS units_sold FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.name ORDER BY units_sold DESC LIMIT 3;
```

**Result:**
```
Nimbus Wireless Mouse | 3093
Terra Coffee Beans 1kg | 2138
Pulse Bluetooth Speaker | 1004
```
