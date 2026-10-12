from __future__ import annotations

from io import BytesIO
from typing import TypedDict
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from src.config import CLEAN_DIR


class SummaryMetrics(TypedDict):
    total_available: int
    total_requested: int
    total_supplied: int
    total_pending: int
    potential_shortage: int
    shortage_by_group: pd.DataFrame
    overall_fulfillment_percentage: float
    total_donations: int
    average_donation_units: float
    inventory_by_group: pd.DataFrame
    hospital_requests: pd.DataFrame
    donation_trend: pd.DataFrame


class AnalyticsResults(TypedDict):
    metrics: SummaryMetrics
    inventory_by_group: pd.DataFrame
    hospital_summary: pd.DataFrame
    demand_by_group: pd.DataFrame
    shortage_by_group: pd.DataFrame
    low_stock: pd.DataFrame
    donation_trends: dict[str, pd.DataFrame]
    donation_breakdowns: dict[str, pd.DataFrame]
    top_hospitals: pd.DataFrame
    greatest_shortages: pd.DataFrame
    descriptive_statistics: pd.DataFrame


def read_clean_csv(name: str) -> pd.DataFrame:
    path = CLEAN_DIR / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def filter_analytics_frame(
    frame: pd.DataFrame,
    filters: dict[str, object],
    date_column: str | None = None,
) -> pd.DataFrame:
    """Apply dashboard date, blood-group, hospital, location, and bank filters."""
    if frame.empty:
        return frame.copy()
    filtered = frame.copy()

    date_column = date_column or next(
        (
            column
            for column in ("request_date", "donation_date", "last_updated")
            if column in filtered.columns
        ),
        None,
    )
    if date_column and date_column in filtered.columns:
        dates = pd.to_datetime(filtered[date_column], errors="coerce")
        date_mask = dates.notna()
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        if start_date is not None:
            date_mask &= dates >= pd.Timestamp(start_date)
        if end_date is not None:
            end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)
            date_mask &= dates < end_exclusive
        filtered = filtered.loc[date_mask].copy()
        filtered[date_column] = dates.loc[date_mask]

    for column, filter_name in (
        ("blood_group", "blood_group"),
        ("hospital_name", "hospital"),
        ("location", "location"),
        ("bank_name", "blood_bank"),
    ):
        value = filters.get(filter_name)
        if column in filtered.columns and value not in (None, "All"):
            filtered = filtered[filtered[column] == value]
    return filtered.reset_index(drop=True)


def get_inventory_summary(inventory: pd.DataFrame | None = None) -> pd.DataFrame:
    df = read_clean_csv("blood_inventory") if inventory is None else inventory
    if df.empty:
        return pd.DataFrame(
            columns=["blood_group", "available_units", "inventory_percentage"]
        )
    summary = (
        df.groupby("blood_group", as_index=False)["available_units"]
        .sum()
        .sort_values("available_units", ascending=False)
        .reset_index(drop=True)
    )
    total_units = summary["available_units"].sum()
    summary["inventory_percentage"] = (
        summary["available_units"] / total_units * 100 if total_units else 0.0
    )
    return summary


def get_hospital_request_summary(requests: pd.DataFrame | None = None) -> pd.DataFrame:
    df = read_clean_csv("hospital_requests") if requests is None else requests
    columns = [
        "hospital_name",
        "requested_units",
        "supplied_units",
        "pending_units",
        "fulfillment_percentage",
    ]
    if df.empty:
        return pd.DataFrame(columns=columns)
    summary = df.groupby("hospital_name", as_index=False).agg(
        requested_units=("requested_units", "sum"),
        supplied_units=("supplied_units", "sum"),
        pending_units=("pending_units", "sum"),
    )
    summary["fulfillment_percentage"] = (
        summary["supplied_units"] / summary["requested_units"] * 100
    ).where(summary["requested_units"] > 0, 0).round(2)
    return summary.sort_values(
        "requested_units", ascending=False
    ).reset_index(drop=True)


def get_donation_trend(donations: pd.DataFrame | None = None) -> pd.DataFrame:
    df = read_clean_csv("donations") if donations is None else donations
    if df.empty:
        return pd.DataFrame(columns=["date", "donation_units"])

    df = df.copy()
    df["date"] = pd.to_datetime(df["donation_date"], errors="coerce").dt.normalize()
    daily = (
        df.dropna(subset=["date"])
        .groupby("date", as_index=False)
        .agg(donation_units=("donation_units", "sum"))
    )
    return daily.sort_values("date").reset_index(drop=True)


def get_donation_period_trend(
    donations: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """Aggregate donated units by day, Monday-starting week, or calendar month."""
    if period not in {"day", "week", "month"}:
        raise ValueError("period must be 'day', 'week', or 'month'")
    if donations.empty:
        return pd.DataFrame(columns=["period", "donation_units"])

    frame = donations.copy()
    dates = pd.to_datetime(frame["donation_date"], errors="coerce")
    frame = frame.loc[dates.notna()].copy()
    frame["period"] = dates.loc[frame.index].dt.normalize()
    if period == "week":
        frame["period"] = frame["period"].dt.to_period("W-SUN").dt.start_time
    elif period == "month":
        frame["period"] = frame["period"].dt.to_period("M").dt.start_time
    return (
        frame.groupby("period", as_index=False)
        .agg(donation_units=("donation_units", "sum"))
        .sort_values("period")
        .reset_index(drop=True)
    )


def get_donation_breakdown(
    donations: pd.DataFrame,
    dimension: str,
) -> pd.DataFrame:
    if dimension not in {"blood_group", "bank_name", "location"}:
        raise ValueError("dimension must be blood_group, bank_name, or location")
    if donations.empty:
        return pd.DataFrame(
            columns=[dimension, "donation_units", "donation_count"]
        )
    return (
        donations.groupby(dimension, as_index=False)
        .agg(
            donation_units=("donation_units", "sum"),
            donation_count=("donation_id", "count")
            if "donation_id" in donations
            else ("donation_units", "count"),
        )
        .sort_values("donation_units", ascending=False)
        .reset_index(drop=True)
    )


def get_demand_by_blood_group(requests: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "blood_group",
        "requested_units",
        "supplied_units",
        "pending_units",
        "fulfillment_percentage",
    ]
    if requests.empty:
        return pd.DataFrame(columns=columns)
    result = requests.groupby("blood_group", as_index=False).agg(
        requested_units=("requested_units", "sum"),
        supplied_units=("supplied_units", "sum"),
        pending_units=("pending_units", "sum"),
    )
    result["fulfillment_percentage"] = (
        result["supplied_units"] / result["requested_units"] * 100
    ).where(result["requested_units"] > 0, 0).round(2)
    return result


def get_shortage_by_blood_group(
    inventory: pd.DataFrame,
    requests: pd.DataFrame,
) -> pd.DataFrame:
    """Estimate shortages by group; this is not a clinical allocation model."""
    if inventory.empty:
        available = pd.Series(dtype="int64", name="available_units")
    else:
        available = inventory.groupby("blood_group")["available_units"].sum()

    if requests.empty:
        pending = pd.Series(dtype="int64", name="pending_units")
    else:
        pending = requests.groupby("blood_group")["pending_units"].sum()

    result = pd.concat([available, pending], axis=1).fillna(0)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "blood_group",
                "available_units",
                "pending_units",
                "potential_shortage",
            ]
        )
    result = result.rename_axis("blood_group").reset_index()
    result["available_units"] = result["available_units"].astype(int)
    result["pending_units"] = result["pending_units"].astype(int)
    result["potential_shortage"] = (
        result["pending_units"] - result["available_units"]
    ).clip(lower=0)
    return result.sort_values("blood_group").reset_index(drop=True)


def get_descriptive_statistics(
    inventory: pd.DataFrame,
    donations: pd.DataFrame,
    requests: pd.DataFrame,
) -> pd.DataFrame:
    measures = (
        ("Inventory per bank/group record", inventory, "available_units"),
        ("Donation units per donation record", donations, "donation_units"),
        ("Requested units per request", requests, "requested_units"),
        ("Supplied units per request", requests, "supplied_units"),
        ("Pending units per request", requests, "pending_units"),
    )
    rows: list[dict[str, object]] = []
    for label, frame, column in measures:
        values = (
            pd.to_numeric(frame[column], errors="coerce").dropna()
            if column in frame
            else pd.Series(dtype="float64")
        )
        rows.append(
            {
                "measure": label,
                "observations": int(values.size),
                "mean_units": values.mean() if values.size else float("nan"),
                "median_units": values.median() if values.size else float("nan"),
                "minimum_units": values.min() if values.size else float("nan"),
                "maximum_units": values.max() if values.size else float("nan"),
                "std_dev_units": values.std(ddof=1)
                if values.size > 1
                else (0.0 if values.size == 1 else float("nan")),
            }
        )
    return pd.DataFrame(rows)


def get_summary_metrics(
    inventory: pd.DataFrame | None = None,
    donations: pd.DataFrame | None = None,
    requests: pd.DataFrame | None = None,
) -> SummaryMetrics:
    inventory = read_clean_csv("blood_inventory") if inventory is None else inventory
    donations = read_clean_csv("donations") if donations is None else donations
    requests = read_clean_csv("hospital_requests") if requests is None else requests

    total_available = (
        int(inventory["available_units"].sum()) if not inventory.empty else 0
    )
    total_requested = (
        int(requests["requested_units"].sum()) if not requests.empty else 0
    )
    total_supplied = int(requests["supplied_units"].sum()) if not requests.empty else 0
    total_pending = int(requests["pending_units"].sum()) if not requests.empty else 0
    shortage_by_group = get_shortage_by_blood_group(inventory, requests)
    potential_shortage = int(shortage_by_group["potential_shortage"].sum())
    total_donations = (
        int(donations["donation_units"].sum()) if not donations.empty else 0
    )
    avg_donation_units = (
        float(donations["donation_units"].mean()) if not donations.empty else 0.0
    )
    overall_fulfillment_percentage = (
        round((total_supplied / total_requested) * 100, 2)
        if total_requested
        else 0.0
    )

    return {
        "total_available": total_available,
        "total_requested": total_requested,
        "total_supplied": total_supplied,
        "total_pending": total_pending,
        "potential_shortage": potential_shortage,
        "shortage_by_group": shortage_by_group,
        "overall_fulfillment_percentage": overall_fulfillment_percentage,
        "total_donations": total_donations,
        "average_donation_units": avg_donation_units,
        "inventory_by_group": get_inventory_summary(inventory),
        "hospital_requests": get_hospital_request_summary(requests),
        "donation_trend": get_donation_trend(donations),
    }


def get_analytics_results(
    inventory: pd.DataFrame,
    donations: pd.DataFrame,
    requests: pd.DataFrame,
    low_stock_threshold: int,
) -> AnalyticsResults:
    if low_stock_threshold < 0:
        raise ValueError("low_stock_threshold must be non-negative")

    metrics = get_summary_metrics(inventory, donations, requests)
    hospital_summary = get_hospital_request_summary(requests)
    demand_by_group = get_demand_by_blood_group(requests)
    shortage_by_group = get_shortage_by_blood_group(inventory, requests)
    inventory_by_group = get_inventory_summary(inventory)
    low_stock_columns = [
        column
        for column in (
            "inventory_id",
            "bank_name",
            "location",
            "blood_group",
            "available_units",
            "last_updated",
        )
        if column in inventory.columns
    ]
    low_stock = (
        inventory.loc[inventory["available_units"] <= low_stock_threshold]
        .sort_values("available_units")
        .loc[:, low_stock_columns]
        .reset_index(drop=True)
        if not inventory.empty
        else pd.DataFrame(columns=low_stock_columns)
    )
    donation_trends = {
        period: get_donation_period_trend(donations, period)
        for period in ("day", "week", "month")
    }
    donation_breakdowns = {
        dimension: get_donation_breakdown(donations, dimension)
        for dimension in ("blood_group", "bank_name", "location")
    }
    top_hospitals = hospital_summary.head(5).reset_index(drop=True)
    greatest_shortages = (
        shortage_by_group.loc[shortage_by_group["potential_shortage"] > 0]
        .sort_values("potential_shortage", ascending=False)
        .reset_index(drop=True)
    )
    return {
        "metrics": metrics,
        "inventory_by_group": inventory_by_group,
        "hospital_summary": hospital_summary,
        "demand_by_group": demand_by_group,
        "shortage_by_group": shortage_by_group,
        "low_stock": low_stock,
        "donation_trends": donation_trends,
        "donation_breakdowns": donation_breakdowns,
        "top_hospitals": top_hospitals,
        "greatest_shortages": greatest_shortages,
        "descriptive_statistics": get_descriptive_statistics(
            inventory, donations, requests
        ),
    }


def analytics_export_zip(results: AnalyticsResults) -> bytes:
    """Package the selected-data result tables as a downloadable CSV bundle."""
    tables: dict[str, pd.DataFrame] = {
        "inventory_by_blood_group.csv": results["inventory_by_group"],
        "hospital_demand.csv": results["hospital_summary"],
        "demand_by_blood_group.csv": results["demand_by_group"],
        "shortage_by_blood_group.csv": results["shortage_by_group"],
        "low_stock_alerts.csv": results["low_stock"],
        "top_hospitals.csv": results["top_hospitals"],
        "greatest_shortages.csv": results["greatest_shortages"],
        "descriptive_statistics.csv": results["descriptive_statistics"],
    }
    tables.update(
        {
            f"donation_trend_{period}.csv": frame
            for period, frame in results["donation_trends"].items()
        }
    )
    tables.update(
        {
            f"donations_by_{dimension}.csv": frame
            for dimension, frame in results["donation_breakdowns"].items()
        }
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for filename, frame in tables.items():
            archive.writestr(filename, frame.to_csv(index=False))
    return buffer.getvalue()
