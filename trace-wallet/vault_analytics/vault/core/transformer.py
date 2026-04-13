import re
import logging
from collections import defaultdict
from datetime import datetime


class DataTransformer:
    """Advanced data transformer for ApexCharts-ready JSON"""

    @staticmethod
    def transform_for_charts(transactions, mode="monthly"):
        """Convert transactions into chart-ready JSON structure"""
        if not transactions:
            return {"monthly": {}, "categories": {}, "timeline": [], "daily": {}}

        monthly = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0, "fees": 0, "count": 0})
        daily = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0})
        categories = defaultdict(lambda: {"amount": 0, "count": 0})
        weekly = defaultdict(lambda: {"income": 0, "expense": 0, "net": 0})

        for tx in transactions:
            try:
                dt = datetime.fromisoformat(tx.get("date", "").replace("Z", "+00:00"))
                month_key = dt.strftime("%Y-%m")
                day_key = dt.strftime("%Y-%m-%d")
                week_num = dt.isocalendar()[1]
                week_key = f"{dt.year}-W{week_num:02d}"
            except:
                month_key = "unknown"
                day_key = "unknown"
                week_key = "unknown"

            amt = float(tx.get("amount", 0))
            tx_type = tx.get("type", "Expense")
            cat = tx.get("category", "Other")
            fee = float(tx.get("fee", 0)) + float(tx.get("vat", 0))

            if tx_type == "Income":
                monthly[month_key]["income"] += amt
                daily[day_key]["income"] += amt
                weekly[week_key]["income"] += amt
            else:
                monthly[month_key]["expense"] += amt
                daily[day_key]["expense"] += amt
                weekly[week_key]["expense"] += amt
                categories[cat]["amount"] += amt
                categories[cat]["count"] += 1

            monthly[month_key]["fees"] += fee
            monthly[month_key]["count"] += 1
            monthly[month_key]["net"] = monthly[month_key]["income"] - monthly[month_key]["expense"]
            daily[day_key]["net"] = daily[day_key]["income"] - daily[day_key]["expense"]
            weekly[week_key]["net"] = weekly[week_key]["income"] - weekly[week_key]["expense"]

        sorted_months = dict(sorted(monthly.items()))
        sorted_days = dict(sorted(daily.items()))
        sorted_weeks = dict(sorted(weekly.items()))

        return {
            "monthly": {k: {key: round(v, 2) for key, v in val.items()} for k, val in sorted_months.items()},
            "daily": {k: {key: round(v, 2) for key, v in val.items()} for k, val in sorted_days.items()},
            "weekly": {k: {key: round(v, 2) for key, v in val.items()} for k, val in sorted_weeks.items()},
            "categories": dict(categories),
            "timeline": [{"month": k, **v} for k, v in sorted_months.items()],
            "daily_timeline": [{"date": k, **v} for k, v in sorted_days.items()],
        }

    @staticmethod
    def to_apex_series(data: dict, chart_type: str = "area") -> dict:
        """Convert transformer output to ApexCharts series format"""
        timeline = data.get("timeline", [])
        if not timeline:
            return {"series": [], "categories": []}

        income_series = [{"x": t["month"], "y": round(t["income"], 2)} for t in timeline]
        expense_series = [{"x": t["month"], "y": round(t["expense"], 2)} for t in timeline]
        net_series = [{"x": t["month"], "y": round(t["net"], 2)} for t in timeline]

        return {
            "series": [
                {"name": "Income", "data": [t["income"] for t in timeline]},
                {"name": "Expenses", "data": [t["expense"] for t in timeline]},
                {"name": "Net", "data": [t["net"] for t in timeline]}
            ],
            "categories": [t["month"] for t in timeline],
            "donut": {
                "series": [round(v["amount"], 2) for v in data.get("categories", {}).values()],
                "labels": list(data.get("categories", {}).keys())
            }
        }
