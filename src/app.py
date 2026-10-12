from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo.errors import PyMongoError

# Streamlit may run this file with `src/` as its import root. Add the
# project root so package imports work regardless of the terminal directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics import (
    analytics_export_zip,
    filter_analytics_frame,
    get_analytics_results,
)
from src.db.connection import DatabaseConnection
from src.data_generation import BLOOD_GROUPS
from src.db.repository import (
    ValidationError,
    create_hospital_request,
    create_inventory,
    delete_hospital_request,
    delete_inventory,
    install_document_validators,
    run_aggregation_examples,
    update_hospital_request,
    update_inventory,
)


@st.cache_data
def load_dashboard_data() -> tuple[dict[str, pd.DataFrame], str | None]:
    from src.config import CLEAN_DIR

    def load_csv_data() -> dict[str, pd.DataFrame]:
        return {
            "blood_inventory": pd.read_csv(CLEAN_DIR / "blood_inventory.csv"),
            "donations": pd.read_csv(CLEAN_DIR / "donations.csv"),
            "hospital_requests": pd.read_csv(CLEAN_DIR / "hospital_requests.csv"),
            "blood_banks": pd.read_csv(CLEAN_DIR / "blood_banks.csv"),
            "hospitals": pd.read_csv(CLEAN_DIR / "hospitals.csv"),
        }

    connection = DatabaseConnection()
    try:
        database = connection.connect()
    except ConnectionError as exc:
        return load_csv_data(), str(exc)

    try:
        data = {
            "blood_inventory": pd.DataFrame(list(database["blood_inventory"].find({}))),
            "donations": pd.DataFrame(list(database["donations"].find({}))),
            "hospital_requests": pd.DataFrame(list(database["hospital_requests"].find({}))),
            "blood_banks": pd.DataFrame(list(database["blood_banks"].find({}))),
            "hospitals": pd.DataFrame(list(database["hospitals"].find({}))),
        }
        return data, None
    except PyMongoError:
        raise RuntimeError(
            "MongoDB is connected, but dashboard data could not be loaded. "
            "Check database permissions and collection availability."
        ) from None
    finally:
        connection.close()


@st.cache_data(ttl=30)
def load_mongo_aggregations(
    start_date: str,
    end_date: str,
    blood_group: str,
    hospital: str,
    location: str,
    blood_bank: str,
) -> dict[str, list[dict]]:
    connection = DatabaseConnection()
    try:
        database = connection.connect()
        return run_aggregation_examples(
            database,
            {
                "start_date": start_date,
                "end_date": end_date,
                "blood_group": blood_group,
                "hospital": hospital,
                "location": location,
                "blood_bank": blood_bank,
            },
        )
    except PyMongoError:
        raise RuntimeError(
            "MongoDB aggregation failed. Check database permissions and server compatibility."
        ) from None
    finally:
        connection.close()


st.set_page_config(page_title="Blood Bank Management Analytics", layout="wide")
st.title("Blood Bank Management Analytics Dashboard")
if "database_action_message" in st.session_state:
    st.success(st.session_state.pop("database_action_message"))

raw_data, database_status = load_dashboard_data()
if database_status:
    st.warning(f"{database_status} Showing cleaned CSV data instead.")

inventory = raw_data.get("blood_inventory", pd.DataFrame())
requests = raw_data.get("hospital_requests", pd.DataFrame())
donations = raw_data.get("donations", pd.DataFrame())

if inventory.empty and requests.empty and donations.empty:
    st.warning("No dataset found. Run the data preparation script to generate the CSV files and seed the MongoDB database.")
    st.stop()

blood_groups = ["All"] + sorted(set(inventory["blood_group"].dropna().tolist() + requests["blood_group"].dropna().tolist()))
hospitals = ["All"] + sorted(set(requests["hospital_name"].dropna().tolist()))
locations = ["All"] + sorted(set(requests["location"].dropna().tolist() + inventory["location"].dropna().tolist() + donations["location"].dropna().tolist()))
blood_banks = ["All"] + sorted(set(inventory["bank_name"].dropna().tolist() + requests["bank_name"].dropna().tolist()))

with st.sidebar:
    st.header("Filters")
    start_date = st.date_input("Start date", value=pd.to_datetime("2024-01-01").date())
    end_date = st.date_input("End date", value=pd.to_datetime("2025-06-30").date())
    blood_group = st.selectbox("Blood group", blood_groups)
    hospital = st.selectbox("Hospital", hospitals)
    location = st.selectbox("Location", locations)
    blood_bank = st.selectbox("Blood bank", blood_banks)
    inventory_max = (
        int(pd.to_numeric(inventory["available_units"], errors="coerce").max())
        if not inventory.empty
        else 100
    )
    threshold_max = max(100, inventory_max)
    low_stock_threshold = st.slider(
        "Low-stock alert threshold (units)",
        min_value=0,
        max_value=threshold_max,
        value=min(100, threshold_max),
        step=1,
    )

selected_filters = {
    "start_date": pd.Timestamp(start_date),
    "end_date": pd.Timestamp(end_date),
    "blood_group": blood_group,
    "hospital": hospital,
    "location": location,
    "blood_bank": blood_bank,
}

mongo_aggregations = None
if database_status is None:
    try:
        mongo_aggregations = load_mongo_aggregations(
            start_date.isoformat(),
            end_date.isoformat(),
            blood_group,
            hospital,
            location,
            blood_bank,
        )
    except ConnectionError as exc:
        st.error(f"{exc} Aggregation results are unavailable.")
    except RuntimeError as exc:
        st.error(str(exc))

filtered_requests = filter_analytics_frame(requests, selected_filters)
filtered_donations = filter_analytics_frame(donations, selected_filters)
filtered_inventory = filter_analytics_frame(inventory, selected_filters)
analytics_results = get_analytics_results(
    filtered_inventory,
    filtered_donations,
    filtered_requests,
    low_stock_threshold,
)
metrics = analytics_results["metrics"]

st.header("Analytics results")
st.caption(
    "All figures below use the selected date, blood group, hospital, location, "
    "and blood bank filters. The project's generated seed data is synthetic; "
    "results reflect the currently loaded records."
)
with st.container(horizontal=True):
    st.metric("Total inventory", f"{metrics['total_available']:,} units", border=True)
    st.metric("Hospital demand", f"{metrics['total_requested']:,} units", border=True)
    st.metric("Supplied", f"{metrics['total_supplied']:,} units", border=True)
    st.metric("Pending", f"{metrics['total_pending']:,} units", border=True)
    st.metric(
        "Weighted fulfillment",
        f"{metrics['overall_fulfillment_percentage']:.2f}%",
        border=True,
    )
    st.metric("Estimated shortage", f"{metrics['potential_shortage']:,} units", border=True)
st.caption(
    "Fulfillment = total supplied units ÷ total requested units × 100. "
    "Estimated shortage = sum by blood group of max(pending units − available "
    "units, 0). The shortage estimate is simplified and is not a clinical "
    "allocation recommendation."
)

inventory_tab, demand_tab, donations_tab, findings_tab = st.tabs(
    ["Inventory", "Hospital demand", "Donation trends", "Findings and statistics"]
)

with inventory_tab:
    st.subheader("Inventory by blood group")
    inventory_by_group = analytics_results["inventory_by_group"]
    if inventory_by_group.empty:
        st.info("No inventory data for the selected filters.")
    else:
        inventory_fig = px.bar(
            inventory_by_group,
            x="blood_group",
            y="available_units",
            color="blood_group",
            title="Available inventory distribution by blood group",
            labels={
                "blood_group": "Blood group",
                "available_units": "Available units",
            },
            hover_data={"inventory_percentage": ":.2f"},
        )
        inventory_fig.update_layout(
            xaxis_title="Blood group",
            yaxis_title="Available units",
            legend_title_text="Blood group",
        )
        st.plotly_chart(
            inventory_fig,
            width="stretch",
            alt="Available inventory in units by blood group",
        )
        st.dataframe(
            inventory_by_group,
            hide_index=True,
            width="stretch",
            column_config={
                "available_units": st.column_config.NumberColumn(
                    "Available units", format="%d"
                ),
                "inventory_percentage": st.column_config.NumberColumn(
                    "Share of selected inventory", format="%.2f%%"
                ),
            },
            alt="Inventory totals and percentage shares by blood group",
        )
        if "bank_name" in filtered_inventory:
            inventory_by_bank = filtered_inventory.groupby(
                "bank_name", as_index=False
            )["available_units"].sum()
            bank_fig = px.bar(
                inventory_by_bank,
                x="bank_name",
                y="available_units",
                color="bank_name",
                title="Available inventory by blood bank",
                labels={
                    "bank_name": "Blood bank",
                    "available_units": "Available units",
                },
            )
            bank_fig.update_layout(
                xaxis_title="Blood bank",
                yaxis_title="Available units",
                legend_title_text="Blood bank",
            )
            st.plotly_chart(
                bank_fig,
                width="stretch",
                alt="Available inventory units by blood bank",
            )

    st.subheader(f"Low-stock alerts (at or below {low_stock_threshold} units)")
    low_stock = analytics_results["low_stock"]
    if low_stock.empty:
        st.success("No bank-and-blood-group inventory records meet this threshold.")
    else:
        st.dataframe(
            low_stock,
            hide_index=True,
            width="stretch",
            alt="Inventory records at or below the selected low-stock threshold",
        )
    st.caption(
        "Alerts compare each blood-bank/blood-group stock record independently "
        "with the configurable threshold; they are operational indicators."
    )

with demand_tab:
    st.subheader("Hospital demand, supply, pending units, and fulfillment")
    hospital_summary = analytics_results["hospital_summary"]
    if hospital_summary.empty:
        st.info("No hospital request data for the selected filters.")
    else:
        hospital_demand_long = hospital_summary.melt(
            id_vars="hospital_name",
            value_vars=["requested_units", "supplied_units", "pending_units"],
            var_name="measure",
            value_name="units",
        )
        demand_fig = px.bar(
            hospital_demand_long,
            x="hospital_name",
            y="units",
            color="measure",
            barmode="group",
            title="Hospital request volumes",
            labels={
                "hospital_name": "Hospital",
                "units": "Units",
                "measure": "Request measure",
            },
        )
        demand_fig.update_layout(
            xaxis_title="Hospital",
            yaxis_title="Units",
            legend_title_text="Request measure",
        )
        st.plotly_chart(
            demand_fig,
            width="stretch",
            alt="Requested, supplied, and pending units by hospital",
        )
        st.dataframe(
            hospital_summary,
            hide_index=True,
            width="stretch",
            column_config={
                "fulfillment_percentage": st.column_config.NumberColumn(
                    "Weighted fulfillment (%)", format="%.2f%%"
                )
            },
            alt="Hospital-level demand, supply, pending units, and fulfillment",
        )
        fulfillment_fig = px.bar(
            hospital_summary,
            x="hospital_name",
            y="fulfillment_percentage",
            color="hospital_name",
            title="Weighted fulfillment by hospital",
            labels={
                "hospital_name": "Hospital",
                "fulfillment_percentage": "Fulfillment (%)",
            },
        )
        fulfillment_fig.update_layout(
            xaxis_title="Hospital",
            yaxis_title="Weighted fulfillment (%)",
            legend_title_text="Hospital",
        )
        st.plotly_chart(
            fulfillment_fig,
            width="stretch",
            alt="Weighted fulfillment percentage by hospital",
        )

    st.subheader("Demand and estimated shortage by blood group")
    shortage_by_group = analytics_results["shortage_by_group"]
    demand_by_group = analytics_results["demand_by_group"]
    if shortage_by_group.empty:
        st.info("No inventory or request data for the selected filters.")
    else:
        comparison = shortage_by_group.merge(
            demand_by_group.drop(columns=["pending_units"]),
            on="blood_group",
            how="left",
        )
        comparison["requested_units"] = comparison["requested_units"].fillna(0)
        comparison["supplied_units"] = comparison["supplied_units"].fillna(0)
        comparison["fulfillment_percentage"] = comparison[
            "fulfillment_percentage"
        ].fillna(0)
        comparison_long = comparison.melt(
            id_vars="blood_group",
            value_vars=["available_units", "pending_units", "potential_shortage"],
            var_name="measure",
            value_name="units",
        )
        comparison_fig = px.bar(
            comparison_long,
            x="blood_group",
            y="units",
            color="measure",
            barmode="group",
            title="Available stock, pending demand, and shortfall by blood group",
            labels={
                "blood_group": "Blood group",
                "units": "Units",
                "measure": "Measure",
            },
        )
        comparison_fig.update_layout(
            xaxis_title="Blood group",
            yaxis_title="Units",
            legend_title_text="Measure",
        )
        st.plotly_chart(
            comparison_fig,
            width="stretch",
            alt="Available stock, pending demand, and estimated shortage by blood group",
        )
        st.dataframe(
            comparison,
            hide_index=True,
            width="stretch",
            alt="Demand and supply totals with estimated shortage by blood group",
        )
    if not filtered_requests.empty:
        location_summary = filtered_requests.groupby("location", as_index=False).agg(
            requested_units=("requested_units", "sum"),
            supplied_units=("supplied_units", "sum"),
            pending_units=("pending_units", "sum"),
        )
        location_long = location_summary.melt(
            id_vars="location",
            value_vars=["requested_units", "supplied_units", "pending_units"],
            var_name="measure",
            value_name="units",
        )
        location_fig = px.bar(
            location_long,
            x="location",
            y="units",
            color="measure",
            barmode="group",
            title="Hospital demand and supply by location",
            labels={
                "location": "Location",
                "units": "Units",
                "measure": "Request measure",
            },
        )
        location_fig.update_layout(
            xaxis_title="Location",
            yaxis_title="Units",
            legend_title_text="Request measure",
        )
        st.plotly_chart(
            location_fig,
            width="stretch",
            alt="Requested, supplied, and pending units by hospital location",
        )

with donations_tab:
    st.subheader("Donation trends")
    trend_tabs = st.tabs(["Daily", "Weekly", "Monthly"])
    for period, trend_tab in zip(("day", "week", "month"), trend_tabs):
        with trend_tab:
            trend = analytics_results["donation_trends"][period]
            if trend.empty:
                st.info(f"No {period} donation data for the selected filters.")
            else:
                trend_fig = px.line(
                    trend,
                    x="period",
                    y="donation_units",
                    markers=True,
                    title=f"Donated units by {period}",
                    labels={"period": period.title(), "donation_units": "Units donated"},
                )
                trend_fig.update_layout(
                    xaxis_title=period.title(),
                    yaxis_title="Units donated",
                )
                st.plotly_chart(
                    trend_fig,
                    width="stretch",
                    alt=f"Donation units aggregated by {period}",
                )

    st.subheader("Donations by blood group, blood bank, and location")
    breakdown_tabs = st.tabs(["Blood group", "Blood bank", "Location"])
    for dimension, tab in zip(
        ("blood_group", "bank_name", "location"), breakdown_tabs
    ):
        with tab:
            breakdown = analytics_results["donation_breakdowns"][dimension]
            display_name = {
                "blood_group": "blood group",
                "bank_name": "blood bank",
                "location": "location",
            }[dimension]
            if breakdown.empty:
                st.info(f"No donation data by {display_name} for these filters.")
            else:
                breakdown_fig = px.bar(
                    breakdown,
                    x=dimension,
                    y="donation_units",
                    color=dimension,
                    title=f"Donated units by {display_name}",
                    labels={dimension: display_name.title(), "donation_units": "Units donated"},
                )
                breakdown_fig.update_layout(
                    xaxis_title=display_name.title(),
                    yaxis_title="Units donated",
                    legend_title_text=display_name.title(),
                )
                st.plotly_chart(
                    breakdown_fig,
                    width="stretch",
                    alt=f"Donation units grouped by {display_name}",
                )
                st.dataframe(
                    breakdown,
                    hide_index=True,
                    width="stretch",
                    alt=f"Donation unit and record totals by {display_name}",
                )

with findings_tab:
    st.subheader("Top hospitals by requested demand")
    top_hospitals = analytics_results["top_hospitals"]
    if top_hospitals.empty:
        st.info("No hospital demand data for the selected filters.")
    else:
        st.dataframe(
            top_hospitals,
            hide_index=True,
            width="stretch",
            alt="Hospitals ranked by requested units",
        )

    st.subheader("Blood groups with greatest estimated shortage")
    greatest_shortages = analytics_results["greatest_shortages"]
    if greatest_shortages.empty:
        st.success("No positive group-level shortages are estimated for these filters.")
    else:
        st.dataframe(
            greatest_shortages,
            hide_index=True,
            width="stretch",
            alt="Blood groups ranked by estimated shortage",
        )

    st.subheader("Descriptive statistics")
    st.dataframe(
        analytics_results["descriptive_statistics"],
        hide_index=True,
        width="stretch",
        column_config={
            "mean_units": st.column_config.NumberColumn("Mean (units)", format="%.2f"),
            "median_units": st.column_config.NumberColumn(
                "Median (units)", format="%.2f"
            ),
            "minimum_units": st.column_config.NumberColumn(
                "Minimum (units)", format="%.2f"
            ),
            "maximum_units": st.column_config.NumberColumn(
                "Maximum (units)", format="%.2f"
            ),
            "std_dev_units": st.column_config.NumberColumn(
                "Standard deviation (units)", format="%.2f"
            ),
        },
        alt="Mean, median, minimum, maximum, and sample standard deviation in units",
    )
    st.caption(
        "Statistics are computed over individual selected records (inventory "
        "records are bank/group snapshots); standard deviation is sample SD "
        "(n−1). Empty filtered series are shown as missing."
    )

st.download_button(
    "Download selected analytical results (ZIP)",
    analytics_export_zip(analytics_results),
    file_name="blood_bank_analytics_results.zip",
    mime="application/zip",
)

with st.expander("Selected source records"):
    st.dataframe(
        filtered_inventory,
        hide_index=True,
        width="stretch",
        alt="Selected inventory source records",
    )
    st.dataframe(
        filtered_donations,
        hide_index=True,
        width="stretch",
        alt="Selected donation source records",
    )
    st.dataframe(
        filtered_requests,
        hide_index=True,
        width="stretch",
        alt="Selected hospital request source records",
    )

if mongo_aggregations is not None:
    with st.expander("MongoDB aggregation examples"):
        st.caption("These summaries are calculated by MongoDB aggregation pipelines.")
        st.write("Inventory totals by blood bank and blood group")
        st.dataframe(pd.DataFrame(mongo_aggregations["inventory_totals"]), width="stretch")
        st.write("Monthly donation trend")
        st.dataframe(pd.DataFrame(mongo_aggregations["donation_trends"]), width="stretch")
        st.write("Hospital demand and fulfillment")
        st.dataframe(pd.DataFrame(mongo_aggregations["hospital_demand"]), width="stretch")


def execute_database_action(action, success_message: str) -> None:
    connection = DatabaseConnection()
    try:
        database = connection.connect()
        install_document_validators(database)
        action(database)
    except ValidationError as exc:
        st.error(str(exc))
    except ConnectionError as exc:
        st.error(str(exc))
    except PyMongoError:
        st.error(
            "MongoDB operation failed. Check database permissions, indexes, "
            "and the selected record."
        )
    else:
        load_dashboard_data.clear()
        load_mongo_aggregations.clear()
        st.session_state["database_action_message"] = success_message
        st.rerun()
    finally:
        connection.close()


st.header("MongoDB inventory and request management")
if database_status:
    st.info("CRUD is available only with a live MongoDB connection. CSV fallback is read-only.")
else:
    bank_records = raw_data["blood_banks"].to_dict("records")
    hospital_records = raw_data["hospitals"].to_dict("records")
    bank_by_name = {record["bank_name"]: record for record in bank_records}
    hospital_by_name = {record["hospital_name"]: record for record in hospital_records}
    blood_group_options = sorted(set(BLOOD_GROUPS))

    inventory_tab, requests_tab = st.tabs(["Inventory CRUD", "Hospital request CRUD"])
    with inventory_tab:
        st.subheader("Create inventory record")
        with st.form("create_inventory_record"):
            create_inv_id = st.text_input("New inventory ID")
            create_inv_bank = st.selectbox("Inventory blood bank", list(bank_by_name))
            create_inv_group = st.selectbox("Inventory blood group", blood_group_options)
            create_inv_units = st.number_input("Available units", min_value=0, step=1)
            create_inv_date = st.date_input("Inventory update date")
            create_inv_submit = st.form_submit_button("Create inventory")
        if create_inv_submit:
            execute_database_action(
                lambda database: create_inventory(
                    database,
                    {
                        "inventory_id": create_inv_id,
                        "bank_id": bank_by_name[create_inv_bank]["bank_id"],
                        "blood_group": create_inv_group,
                        "available_units": create_inv_units,
                        "last_updated": create_inv_date,
                    },
                ),
                "Inventory record created.",
            )

        inventory_records = raw_data["blood_inventory"].to_dict("records")
        inventory_ids = [record["inventory_id"] for record in inventory_records]
        inventory_by_id = {record["inventory_id"]: record for record in inventory_records}
        if inventory_ids:
            st.subheader("Update inventory record")
            with st.form("update_inventory_record"):
                update_inv_id = st.selectbox("Inventory record to update", inventory_ids)
                existing_inventory = inventory_by_id[update_inv_id]
                update_inv_units = st.number_input(
                    "Updated available units",
                    min_value=0,
                    step=1,
                    value=int(existing_inventory["available_units"]),
                )
                update_inv_date = st.date_input(
                    "Updated inventory date",
                    value=pd.to_datetime(existing_inventory["last_updated"]).date(),
                )
                update_inv_submit = st.form_submit_button("Save inventory update")
            if update_inv_submit:
                execute_database_action(
                    lambda database: update_inventory(
                        database,
                        update_inv_id,
                        available_units=update_inv_units,
                        last_updated=update_inv_date,
                    ),
                    "Inventory record updated.",
                )

            st.subheader("Delete inventory record")
            with st.form("delete_inventory_record"):
                delete_inv_id = st.selectbox("Inventory record to delete", inventory_ids, key="delete_inv_id")
                confirm_inv_delete = st.checkbox("I confirm deletion of this inventory record")
                delete_inv_submit = st.form_submit_button("Delete inventory record")
            if delete_inv_submit:
                execute_database_action(
                    lambda database: delete_inventory(
                        database, delete_inv_id, confirmed=confirm_inv_delete
                    ),
                    "Inventory record deleted.",
                )

    with requests_tab:
        st.subheader("Create hospital request")
        with st.form("create_hospital_request"):
            create_req_id = st.text_input("New request ID")
            create_req_hospital = st.selectbox("Request hospital", list(hospital_by_name))
            create_req_bank = st.selectbox("Request blood bank", list(bank_by_name))
            create_req_group = st.selectbox("Request blood group", blood_group_options)
            create_req_requested = st.number_input("Requested units", min_value=1, step=1)
            create_req_supplied = st.number_input("Supplied units", min_value=0, step=1)
            create_req_date = st.date_input("Request date")
            create_req_priority = st.selectbox("Request priority", ["normal", "urgent"])
            create_req_submit = st.form_submit_button("Create request")
        if create_req_submit:
            execute_database_action(
                lambda database: create_hospital_request(
                    database,
                    {
                        "request_id": create_req_id,
                        "hospital_id": hospital_by_name[create_req_hospital]["hospital_id"],
                        "bank_id": bank_by_name[create_req_bank]["bank_id"],
                        "blood_group": create_req_group,
                        "requested_units": create_req_requested,
                        "supplied_units": create_req_supplied,
                        "request_date": create_req_date,
                        "priority": create_req_priority,
                    },
                ),
                "Hospital request created.",
            )

        request_records = raw_data["hospital_requests"].to_dict("records")
        request_ids = [record["request_id"] for record in request_records]
        request_by_id = {record["request_id"]: record for record in request_records}
        if request_ids:
            st.subheader("Update hospital request")
            with st.form("update_hospital_request"):
                update_req_id = st.selectbox("Request to update", request_ids)
                existing_request = request_by_id[update_req_id]
                update_req_requested = st.number_input(
                    "Updated requested units",
                    min_value=1,
                    step=1,
                    value=int(existing_request["requested_units"]),
                )
                update_req_supplied = st.number_input(
                    "Updated supplied units",
                    min_value=0,
                    step=1,
                    value=int(existing_request["supplied_units"]),
                )
                update_req_priority = st.selectbox(
                    "Updated priority",
                    ["normal", "urgent"],
                    index=0 if existing_request["priority"] == "normal" else 1,
                )
                update_req_submit = st.form_submit_button("Save request update")
            if update_req_submit:
                execute_database_action(
                    lambda database: update_hospital_request(
                        database,
                        update_req_id,
                        requested_units=update_req_requested,
                        supplied_units=update_req_supplied,
                        priority=update_req_priority,
                    ),
                    "Hospital request updated.",
                )

            st.subheader("Delete hospital request")
            with st.form("delete_hospital_request"):
                delete_req_id = st.selectbox("Request to delete", request_ids, key="delete_req_id")
                confirm_req_delete = st.checkbox("I confirm deletion of this hospital request")
                delete_req_submit = st.form_submit_button("Delete hospital request")
            if delete_req_submit:
                execute_database_action(
                    lambda database: delete_hospital_request(
                        database, delete_req_id, confirmed=confirm_req_delete
                    ),
                    "Hospital request deleted.",
                )
