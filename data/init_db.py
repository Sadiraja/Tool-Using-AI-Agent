"""
Database and sample data initializer for Tool-Using AI Agent.
Creates:
- data/company.db (SQLite database with departments, employees, products, sales)
- data/sample_data.csv (Employee IDs and performance targets)
- data/config.json (Department thresholds, tax rates, inventory limits)
- data/company_notes.txt (Quarterly financial projections and notes)
"""

import os
import sqlite3
import json
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "company.db")
CSV_PATH = os.path.join(BASE_DIR, "sample_data.csv")
JSON_PATH = os.path.join(BASE_DIR, "config.json")
TXT_PATH = os.path.join(BASE_DIR, "company_notes.txt")


def init_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create tables
    cur.execute("""
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        manager TEXT NOT NULL,
        budget REAL NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department_id INTEGER NOT NULL,
        salary REAL NOT NULL,
        hire_year INTEGER NOT NULL,
        rating REAL NOT NULL,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    );
    """)

    cur.execute("""
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY,
        product_id INTEGER NOT NULL,
        employee_id INTEGER NOT NULL,
        units_sold INTEGER NOT NULL,
        sale_date TEXT NOT NULL,
        revenue REAL NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    );
    """)

    # Seed departments
    departments = [
        (1, "Engineering", "Alice Johnson", 450000.0),
        (2, "Sales", "Bob Vance", 320000.0),
        (3, "Marketing", "Carol Danvers", 210000.0),
        (4, "Support", "David Miller", 150000.0),
    ]
    cur.executemany("INSERT INTO departments VALUES (?, ?, ?, ?)", departments)

    # Seed employees
    employees = [
        (101, "John Doe", 1, 115000.0, 2019, 4.8),
        (102, "Jane Smith", 1, 125000.0, 2018, 4.9),
        (103, "Alex Wong", 2, 85000.0, 2021, 4.2),
        (104, "Sarah Connor", 2, 92000.0, 2020, 4.6),
        (105, "Michael Scott", 2, 98000.0, 2017, 3.9),
        (106, "Dwight Schrute", 2, 95000.0, 2018, 4.9),
        (107, "Pam Beesly", 3, 65000.0, 2021, 4.1),
        (108, "Jim Halpert", 3, 78000.0, 2019, 4.5),
        (109, "Stanley Hudson", 4, 72000.0, 2016, 4.0),
        (110, "Kevin Malone", 4, 58000.0, 2022, 3.5),
    ]
    cur.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?)", employees)

    # Seed products
    products = [
        (1, "Cloud Server A", "Infrastructure", 450.0, 45),
        (2, "Database Cluster B", "Infrastructure", 1200.0, 12),
        (3, "Enterprise CRM License", "Software", 350.0, 110),
        (4, "Security Suite Pro", "Security", 850.0, 8),
        (5, "Analytics Dashboard", "Software", 250.0, 65),
        (6, "Backup Appliance", "Hardware", 1500.0, 4),
    ]
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?)", products)

    # Seed sales
    sales = [
        (1, 1, 103, 10, "2024-01-15", 4500.0),
        (2, 2, 104, 5, "2024-01-20", 6000.0),
        (3, 3, 106, 25, "2024-02-05", 8750.0),
        (4, 4, 106, 12, "2024-02-14", 10200.0),
        (5, 5, 103, 30, "2024-02-28", 7500.0),
        (6, 1, 104, 15, "2024-03-10", 6750.0),
        (7, 6, 106, 6, "2024-03-22", 9000.0),
        (8, 3, 105, 18, "2024-03-25", 6300.0),
        (9, 2, 103, 4, "2024-04-02", 4800.0),
        (10, 4, 104, 8, "2024-04-18", 6800.0),
    ]
    cur.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)", sales)

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")


def init_files():
    # CSV file
    csv_rows = [
        ["employee_id", "employee_name", "target_tier", "quota_attainment_pct"],
        [103, "Alex Wong", "Tier 2", 108.5],
        [104, "Sarah Connor", "Tier 1", 122.0],
        [105, "Michael Scott", "Tier 3", 94.0],
        [106, "Dwight Schrute", "Tier 1", 145.2],
    ]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"CSV file created at {CSV_PATH}")

    # JSON config
    config = {
        "inventory_thresholds": {
            "Infrastructure": 15,
            "Software": 20,
            "Security": 10,
            "Hardware": 5
        },
        "bonus_multipliers": {
            "Tier 1": 0.15,
            "Tier 2": 0.10,
            "Tier 3": 0.05
        },
        "corporate_tax_rate": 0.21,
        "discount_rate": 0.08
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    print(f"Config JSON created at {JSON_PATH}")

    # Text notes
    notes = (
        "QUARTERLY FINANCIAL & STRATEGIC PROJECTIONS (FY2024)\n"
        "====================================================\n"
        "Department Targets:\n"
        "- Sales Q1 Revenue Benchmark Target: $65,000.00\n"
        "- Engineering Research Overhead Allocation: 14.5% of department budget\n"
        "- Minimum Acceptable Stock Margin: 12 units for mission-critical hardware/security items\n\n"
        "Bonus Computation Policy:\n"
        "Bonus payout = Base Salary * Bonus Tier Multiplier * (Quota Attainment / 100)\n\n"
        "External Competitor Intel:\n"
        "Competitor Apex Dynamics posted Q1 cloud revenues of $84,200.00.\n"
        "Our internal target was to achieve at least 80% of Apex Dynamics cloud sales volume.\n"
    )
    with open(TXT_PATH, "w", encoding="utf-8") as f:
        f.write(notes)
    print(f"Notes TXT created at {TXT_PATH}")


if __name__ == "__main__":
    init_database()
    init_files()
