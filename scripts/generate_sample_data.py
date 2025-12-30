"""
Generate Sample Data
====================
Creates test datasets for Shortcut Bridge testing.

Run: python scripts/generate_sample_data.py

Outputs:
  - data/samples/sales_transactions.csv (1000 rows)
  - data/samples/financial_assumptions.json
  - data/samples/employee_metrics.json
  - data/samples/time_series_data.csv (365 days)
"""

import csv
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Output directory
SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


def generate_sales_transactions(n_rows: int = 1000) -> None:
    """Generate sales transaction data."""
    print(f"Generating sales_transactions.csv ({n_rows} rows)...")
    
    products = ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Service Plan", "Subscription"]
    regions = ["North", "South", "East", "West", "Central"]
    
    rows = []
    start_date = datetime(2025, 1, 1)
    
    for i in range(n_rows):
        date = start_date + timedelta(days=random.randint(0, 364))
        product = random.choice(products)
        quantity = random.randint(1, 50)
        unit_price = round(random.uniform(10, 500), 2)
        
        rows.append({
            "transaction_id": f"TXN-{i+1:05d}",
            "date": date.strftime("%Y-%m-%d"),
            "customer_id": f"CUST-{random.randint(1000, 9999)}",
            "product": product,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": round(quantity * unit_price, 2),
            "region": random.choice(regions)
        })
    
    output_path = SAMPLES_DIR / "sales_transactions.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  [OK] Saved to {output_path}")


def generate_financial_assumptions() -> None:
    """Generate financial model assumptions."""
    print("Generating financial_assumptions.json...")
    
    data = {
        "model_name": "FY2025 Financial Model",
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "scenarios": [
            {
                "name": "Base Case",
                "revenue_growth_pct": 0.08,
                "cogs_pct": 0.45,
                "opex_growth_pct": 0.05,
                "tax_rate": 0.21,
                "discount_rate": 0.10
            },
            {
                "name": "Upside Case",
                "revenue_growth_pct": 0.15,
                "cogs_pct": 0.42,
                "opex_growth_pct": 0.06,
                "tax_rate": 0.21,
                "discount_rate": 0.10
            },
            {
                "name": "Downside Case",
                "revenue_growth_pct": 0.02,
                "cogs_pct": 0.50,
                "opex_growth_pct": 0.03,
                "tax_rate": 0.21,
                "discount_rate": 0.12
            }
        ],
        "base_metrics": {
            "revenue_fy2024": 10000000,
            "cogs_fy2024": 4500000,
            "opex_fy2024": 3000000,
            "shares_outstanding": 1000000
        }
    }
    
    output_path = SAMPLES_DIR / "financial_assumptions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"  [OK] Saved to {output_path}")


def generate_employee_metrics() -> None:
    """Generate employee performance data."""
    print("Generating employee_metrics.json...")
    
    departments = ["Engineering", "Sales", "Marketing", "Finance", "Operations", "HR"]
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Quinn", "Avery"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
    
    employees = []
    for i in range(50):
        dept = random.choice(departments)
        base_salary = {
            "Engineering": 120000, "Sales": 80000, "Marketing": 75000,
            "Finance": 90000, "Operations": 70000, "HR": 65000
        }[dept]
        
        employees.append({
            "employee_id": f"EMP-{i+1:04d}",
            "name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "department": dept,
            "salary": base_salary + random.randint(-10000, 30000),
            "performance_score": round(random.uniform(2.5, 5.0), 1),
            "tenure_years": random.randint(0, 15),
            "is_manager": random.random() < 0.2
        })
    
    data = {
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "total_employees": len(employees),
        "employees": employees
    }
    
    output_path = SAMPLES_DIR / "employee_metrics.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    print(f"  [OK] Saved to {output_path}")


def generate_time_series_data(n_days: int = 365) -> None:
    """Generate daily time series metrics."""
    print(f"Generating time_series_data.csv ({n_days} days)...")
    
    rows = []
    start_date = datetime(2025, 1, 1)
    
    # Initialize with base values
    metric_a = 1000
    metric_b = 500
    metric_c = 250
    
    for i in range(n_days):
        date = start_date + timedelta(days=i)
        
        # Add some trend and noise
        metric_a = max(0, metric_a + random.uniform(-20, 25))
        metric_b = max(0, metric_b + random.uniform(-15, 18))
        metric_c = max(0, metric_c + random.uniform(-10, 12))
        
        rows.append({
            "date": date.strftime("%Y-%m-%d"),
            "metric_a": round(metric_a, 2),
            "metric_b": round(metric_b, 2),
            "metric_c": round(metric_c, 2)
        })
    
    output_path = SAMPLES_DIR / "time_series_data.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"  [OK] Saved to {output_path}")


def main():
    print("\n" + "=" * 50)
    print("  GENERATING SAMPLE DATA")
    print("=" * 50 + "\n")
    
    generate_sales_transactions(1000)
    generate_financial_assumptions()
    generate_employee_metrics()
    generate_time_series_data(365)
    
    print("\n" + "=" * 50)
    print("  COMPLETE")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()

