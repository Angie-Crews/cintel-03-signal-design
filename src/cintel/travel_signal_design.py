"""travel_signal_design.py - Missouri travel expenditure signal design project.

Author: Angie Crews
Date: 2026-11-01

This project analyzes Missouri state expenditure data to create
useful signals for monitoring travel spending and identifying
unusual spending patterns.
"""

from pathlib import Path
from typing import Final

import matplotlib.pyplot as plt
import polars as pl

# === DECLARE FILE PATHS ===

ROOT_DIR: Final[Path] = Path.cwd()
DATA_DIR: Final[Path] = ROOT_DIR / "data"
ARTIFACTS_DIR: Final[Path] = ROOT_DIR / "artifacts"
IMAGES_DIR: Final[Path] = ROOT_DIR / "docs" / "images"

DATA_FILE: Final[Path] = DATA_DIR / "2026_State_Expenditures_20261029.csv"
OUTPUT_FILE: Final[Path] = ARTIFACTS_DIR / "missouri_travel_signals.csv"
CHART_FILE: Final[Path] = IMAGES_DIR / "travel_spending_by_agency.png"


def main() -> None:
    """Create signals for monitoring Missouri travel expenditures."""
    # ----------------------------------------------------
    # STEP 1: LOAD THE MISSOURI EXPENDITURE DATA
    # ----------------------------------------------------

    df: pl.DataFrame = pl.read_csv(DATA_FILE)

    print(f"Loaded {df.height:,} expenditure records")

    # ----------------------------------------------------
    # STEP 2: CONVERT PAYMENT AMOUNTS TO NUMERIC VALUES
    # ----------------------------------------------------

    # Keep the original Payments Total column and create
    # a numeric version that can be used for calculations.
    df = df.with_columns(
        pl.col("Payments Total")
        .str.replace_all(",", "")
        .cast(pl.Float64)
        .alias("payment_amount")
    )

    # ----------------------------------------------------
    # STEP 3: KEEP ONLY TRAVEL EXPENDITURES
    # ----------------------------------------------------

    travel_df = df.filter(pl.col("Category Description") == "TRAVEL")

    # ----------------------------------------------------
    # STEP 4: CALCULATE AVERAGE TRAVEL SPENDING BY AGENCY
    # ----------------------------------------------------

    # Calculate the average travel payment for each agency.
    agency_avg = travel_df.group_by("Agency Name").agg(
        pl.col("payment_amount").mean().alias("agency_avg_travel")
    )

    # ----------------------------------------------------
    # STEP 5: CREATE TRAVEL SPENDING SIGNALS
    # ----------------------------------------------------

    # Add the agency average to each travel expenditure.
    signals_df = travel_df.join(agency_avg, on="Agency Name", how="left")

    # Compare each payment with the average payment for its agency.
    signals_df = signals_df.with_columns(
        (pl.col("payment_amount") / pl.col("agency_avg_travel"))
        .round(2)
        .alias("relative_to_agency_avg")
    )

    # ----------------------------------------------------
    # STEP 6: SUMMARIZE TRAVEL SPENDING BY AGENCY
    # ----------------------------------------------------

    # Calculate total and average travel spending for each agency.
    agency_summary = (
        signals_df.group_by("Agency Name")
        .agg(
            [
                pl.col("payment_amount").sum().alias("total_travel_spending"),
                pl.col("payment_amount").mean().alias("average_travel_payment"),
                pl.len().alias("travel_payment_count"),
            ]
        )
        .sort("total_travel_spending", descending=True)
    )

    # Keep the top 10 agencies by total travel spending for the visualization.
    top_agencies = agency_summary.head(10)

    # ----------------------------------------------------
    # STEP 7: SAVE TRAVEL SIGNALS AS EVIDENCE
    # ----------------------------------------------------

    # Ensure the artifacts folder exists.
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save the travel records with the new signal columns.
    signals_df.write_csv(OUTPUT_FILE)

    # ----------------------------------------------------
    # STEP 8: CREATE THE VISUALIZATION
    # ----------------------------------------------------

    # Ensure the documentation images folder exists.
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Reverse the order so the agency with the highest
    # total travel spending appears at the top.
    agency_names = top_agencies["Agency Name"].to_list()[::-1]
    travel_totals = top_agencies["total_travel_spending"].to_list()[::-1]

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(agency_names, travel_totals)

    ax.set_title("Top 10 Agencies by Total Travel Spending")
    ax.set_xlabel("Total Travel Spending ($)")
    ax.set_ylabel("Agency")

    # Add the dollar amount at the end of each bar.
    for bar, total in zip(bars, travel_totals, strict=True):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f"${total:,.0f}",
            va="center",
        )

    fig.tight_layout()
    fig.savefig(CHART_FILE, dpi=150)
    plt.close(fig)

    # ----------------------------------------------------
    # STEP 9: DISPLAY RESULTS
    # ----------------------------------------------------

    print(f"Travel expenditure records: {travel_df.height:,}")
    print(f"Travel signal records created: {signals_df.height:,}")
    print(f"Results saved to: {OUTPUT_FILE}")
    print(f"Chart saved to: {CHART_FILE}")
    print("Top 10 agencies by total travel spending:")
    print(top_agencies)


if __name__ == "__main__":
    main()
