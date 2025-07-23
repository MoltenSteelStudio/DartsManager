import streamlit as st
import pandas as pd
import os
from datetime import datetime
import streamlit.components.v1 as components



# --- Constants ---
BALANCE_FILE = "balance_sheet.csv"
PAYMENT_FILE = "payment_sheet.csv"
VENUE_FILE = "venue_sheet.csv"
PLAYER_FILE = "player_sheet.csv"
EXPENSE_FILE = "expense_sheet.csv"
OTHER_INCOME_FILE = "other_income_sheet.csv"

CATEGORY_AMOUNTS = {"Subs": 2.0, "Raffle": 1.0, "Food": 1.0}

# --- Initialize files ---
def init_files():
    if not os.path.exists(BALANCE_FILE):
        pd.DataFrame(columns=["Venue", "Date", "Total Player Income", "Other Income", "Total Expenses", "Net"]).to_csv(BALANCE_FILE, index=False)
    if not os.path.exists(PAYMENT_FILE):
        pd.DataFrame(columns=["Name", "Amount", "Category", "Venue", "Date"]).to_csv(PAYMENT_FILE, index=False)
    if not os.path.exists(VENUE_FILE):
        pd.DataFrame(columns=["Venue", "Date"]).to_csv(VENUE_FILE, index=False)
    if not os.path.exists(PLAYER_FILE):
        pd.DataFrame(columns=["Name"]).to_csv(PLAYER_FILE, index=False)
    if not os.path.exists(EXPENSE_FILE):
        pd.DataFrame(columns=["Venue", "Date", "Amount", "Description"]).to_csv(EXPENSE_FILE, index=False)
    if not os.path.exists(OTHER_INCOME_FILE):
        pd.DataFrame(columns=["Venue", "Date", "Raffle Income", "Fines"]).to_csv(OTHER_INCOME_FILE, index=False)

# --- Load data ---
def load_data():
    return (
        pd.read_csv(BALANCE_FILE),
        pd.read_csv(PAYMENT_FILE),
        pd.read_csv(VENUE_FILE),
        pd.read_csv(PLAYER_FILE),
        pd.read_csv(EXPENSE_FILE),
        pd.read_csv(OTHER_INCOME_FILE),
    )

# --- Save data ---
def save_data(balance, payment, venue, player, expense, other_income):
    balance.to_csv(BALANCE_FILE, index=False)
    payment.to_csv(PAYMENT_FILE, index=False)
    venue.to_csv(VENUE_FILE, index=False)
    player.to_csv(PLAYER_FILE, index=False)
    expense.to_csv(EXPENSE_FILE, index=False)
    other_income.to_csv(OTHER_INCOME_FILE, index=False)

# --- Recalculate balance ---
def recalculate_balance(payment_df, expenses_df, other_income_df):
    player_income = payment_df.groupby(["Venue", "Date"], as_index=False)["Amount"].sum()
    player_income.rename(columns={"Amount": "Total Player Income"}, inplace=True)

    expenses = expenses_df.groupby(["Venue", "Date"], as_index=False)["Amount"].sum()
    expenses.rename(columns={"Amount": "Total Expenses"}, inplace=True)

    other_income_df["Other Income"] = other_income_df[["Raffle Income", "Fines"]].sum(axis=1)

    merged = pd.merge(player_income, other_income_df[["Venue", "Date", "Other Income"]], on=["Venue", "Date"], how="outer")
    merged = pd.merge(merged, expenses, on=["Venue", "Date"], how="outer")

    merged.fillna(0, inplace=True)
    merged["Net"] = merged["Total Player Income"] + merged["Other Income"] - merged["Total Expenses"]

    return merged

# --- App Setup ---
# Inject manifest and icons for PWA support
components.html(
    """
    <link rel="manifest" href="/manifest.json">
    <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
    <link rel="apple-touch-icon" href="/icon-512.png">
    <meta name="theme-color" content="#4CAF50">
    """,
    height=0
)

st.set_page_config(
    page_title="🎯 Custom Darts App",  # Custom Title
    page_icon="🎯",  # Custom Icon
    layout="wide",
    initial_sidebar_state="expanded"
)

init_files()
balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df = load_data()

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👥 Player Management",
    "📍 Venue Management",
    "💵 Income & Expense",
    "📊 Balance Sheet",
    "📋 Log",
    "🧹 Clear Data",

])

# --- Tab 1: Player Management ---
with tab1:
    st.subheader("Add New Player")
    with st.form("add_player_form"):
        new_player = st.text_input("Player Name")
        if st.form_submit_button("Add Player"):
            if new_player.strip() and new_player not in players_df["Name"].tolist():
                players_df = pd.concat([players_df, pd.DataFrame({"Name": [new_player.strip()]})], ignore_index=True)
                save_data(balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df)
                st.success(f"Player '{new_player}' added.")
                st.rerun()
            else:
                st.warning("Invalid or duplicate name.")

    st.subheader("Current Players")
    st.dataframe(players_df)
    st.download_button("Download Players CSV", players_df.to_csv(index=False), "players.csv")

    st.subheader("❌ Remove Player")
    player_to_remove = st.selectbox("Select Player to Remove", players_df["Name"])
    if st.button("Remove Selected Player"):
        player_payments = payment_df[payment_df["Name"] == player_to_remove]
        total_contributed = player_payments["Amount"].sum()

        venues_played = player_payments[["Venue", "Date"]].drop_duplicates()
        contribution_results = []

        for _, row in venues_played.iterrows():
            venue = row["Venue"]
            date = row["Date"]
            try:
                net = balance_df[(balance_df["Venue"] == venue) & (balance_df["Date"] == date)]["Net"].values[0]
            except IndexError:
                net = 0.0
            players_in_game = payment_df[(payment_df["Venue"] == venue) & (payment_df["Date"] == date)]["Name"].nunique()
            value_share = net / (players_in_game - 1) if players_in_game > 1 else 0
            contribution_results.append({
                "Venue": venue,
                "Date": date,
                "Value Per Remaining Player": round(value_share, 2)
            })

        # Remove player data
        players_df = players_df[players_df["Name"] != player_to_remove]
        payment_df = payment_df[payment_df["Name"] != player_to_remove]

        # Recalculate balance and save
        balance_df = recalculate_balance(payment_df, expenses_df, other_income_df)
        save_data(balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df)

        st.success(f"Removed {player_to_remove}. Total contributed: £{total_contributed:.2f}")
        st.dataframe(pd.DataFrame(contribution_results))
        st.rerun()

# --- Tab 2: Venue Management ---
with tab2:
    st.subheader("Add New Venue")
    with st.form("add_venue_form"):
        venue_name = st.text_input("Venue Name")
        venue_date = st.date_input("Match Date")
        if st.form_submit_button("Add Venue"):
            venue_str = venue_name.strip()
            date_str = venue_date.strftime("%d-%m-%Y")
            exists = not venues_df[
                (venues_df["Venue"] == venue_str) & (venues_df["Date"] == date_str)
            ].empty
            if venue_str and not exists:
                venues_df = pd.concat([venues_df, pd.DataFrame({"Venue": [venue_str], "Date": [date_str]})], ignore_index=True)
                save_data(balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df)
                st.success(f"Venue '{venue_str}' on {date_str} added.")
                st.rerun()
            else:
                st.warning("Invalid or duplicate venue/date.")

    st.subheader("Current Venues")
    st.dataframe(venues_df)
    st.download_button("Download Venues CSV", venues_df.to_csv(index=False), "venues.csv")

# --- Tab 3: Income and Expense ---
with tab3:
    venue_display = [f"{v} ({d})" for v, d in zip(venues_df["Venue"], venues_df["Date"])]

    # --- Select match at top ---
    st.subheader("🎯 Selected Match Context")
    selected_match = st.selectbox("Venue & Date", venue_display, key="selected_match_context")

    if selected_match and " (" in selected_match:
        selected_venue, selected_date_str = selected_match.split(" (")
        selected_date = selected_date_str.replace(")", "")
    else:
        st.warning("Please select a valid match.")
        st.stop()

    st.divider()

    # --- Player Payment Section ---
    st.subheader("👤 Per Player Income")

    def update_payment_checkboxes():
        name = st.session_state.selected_name
        existing = payment_df[
            (payment_df["Name"] == name) &
            (payment_df["Venue"] == selected_venue) &
            (payment_df["Date"] == selected_date)
        ]
        st.session_state.subs_paid = not existing[existing["Category"] == "Subs"].empty
        st.session_state.raffle_paid = not existing[existing["Category"] == "Raffle"].empty
        st.session_state.food_paid = not existing[existing["Category"] == "Food"].empty

    name = st.selectbox("Player Name", players_df["Name"].tolist(), key="selected_name", on_change=update_payment_checkboxes)

    # Checkboxes reflect session state
    subs = st.checkbox("Subs (£2.00)", value=st.session_state.get("subs_paid", False), key="subs_paid")
    raffle = st.checkbox("Raffle (£1.00)", value=st.session_state.get("raffle_paid", False), key="raffle_paid")
    food = st.checkbox("Food (£1.00)", value=st.session_state.get("food_paid", False), key="food_paid")

    with st.form("payment_form"):
        st.markdown("### ➕ Add / Update Payment")
        rows = []
        if subs: rows.append({"Name": name, "Amount": 2.0, "Category": "Subs", "Venue": selected_venue, "Date": selected_date})
        if raffle: rows.append({"Name": name, "Amount": 1.0, "Category": "Raffle", "Venue": selected_venue, "Date": selected_date})
        if food: rows.append({"Name": name, "Amount": 1.0, "Category": "Food", "Venue": selected_venue, "Date": selected_date})

        if st.form_submit_button("Add / Update Payment"):
            total_payment = sum(r["Amount"] for r in rows)
            if total_payment > 4:
                st.error("Total payment cannot exceed £4.")
            else:
                keep_categories = []
                if subs: keep_categories.append("Subs")
                if raffle: keep_categories.append("Raffle")
                if food: keep_categories.append("Food")

                # Remove outdated entries
                payment_df = payment_df[~(
                    (payment_df["Name"] == name) &
                    (payment_df["Venue"] == selected_venue) &
                    (payment_df["Date"] == selected_date) &
                    (~payment_df["Category"].isin(keep_categories))
                )]

                # Add new
                if rows:
                    payment_df = pd.concat([payment_df, pd.DataFrame(rows)], ignore_index=True)

                # Save and update
                balance_df = recalculate_balance(payment_df, expenses_df, other_income_df)
                save_data(balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df)
                st.success("Payment added/updated.")
                st.rerun()

    st.divider()

    # --- Expenses & Other Income ---
    st.subheader("💸 Add Expense / Other Income")
    with st.form("add_expense_income"):
        amount = st.number_input("Expense Amount", min_value=0.0, step=0.5)
        desc = st.text_input("Expense Description")
        raffle_income = st.number_input("Raffle Income", min_value=0.0, step=0.5)
        fines = st.number_input("Fines", min_value=0.0, step=0.5)

        if st.form_submit_button("Submit Expense/Income"):
            if amount > 0:
                expenses_df = pd.concat([expenses_df, pd.DataFrame({
                    "Venue": [selected_venue],
                    "Date": [selected_date],
                    "Amount": [amount],
                    "Description": [desc]
                })], ignore_index=True)

            if raffle_income > 0 or fines > 0:
                mask = (other_income_df["Venue"] == selected_venue) & (other_income_df["Date"] == selected_date)
                if not other_income_df[mask].empty:
                    other_income_df.loc[mask, "Raffle Income"] = raffle_income
                    other_income_df.loc[mask, "Fines"] = fines
                else:
                    other_income_df = pd.concat([other_income_df, pd.DataFrame({
                        "Venue": [selected_venue],
                        "Date": [selected_date],
                        "Raffle Income": [raffle_income],
                        "Fines": [fines]
                    })], ignore_index=True)

            balance_df = recalculate_balance(payment_df, expenses_df, other_income_df)
            save_data(balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df)
            st.success("Expense/Income saved.")
            st.rerun()

    st.divider()

    # --- Match Summary (at bottom, horizontal) ---
    st.markdown("### 💹 Match Summary")

    match_summary = balance_df[
        (balance_df["Venue"] == selected_venue) &
        (balance_df["Date"] == selected_date)
    ]

    if not match_summary.empty:
        row = match_summary.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Player Income", f"£{row['Total Player Income']:.2f}")
        col2.metric("Other Income", f"£{row['Other Income']:.2f}")
        col3.metric("Expenses", f"£{row['Total Expenses']:.2f}")
        col4.metric("Net", f"£{row['Net']:.2f}")
    else:
        st.info("No financial summary yet for this match.")

# --- Tab 4: Balance Sheet ---
with tab4:
    st.subheader("📊 Player Contributions by Match (Columns)")

    # All unique matches (venue + date)
    match_keys = venues_df.copy()
    match_keys["Venue_Date"] = match_keys["Venue"] + " - " + match_keys["Date"]

    # Prepare base dataframe with all players
    all_players = players_df["Name"].unique()

    # Sum payment per player per match
    payment_summary = payment_df.groupby(["Name", "Venue", "Date"])["Amount"].sum().reset_index()
    payment_summary["Venue_Date"] = payment_summary["Venue"] + " - " + payment_summary["Date"]

    # Create pivot with players as rows, matches as columns
    pivot = payment_summary.pivot(index="Name", columns="Venue_Date", values="Amount")

    # Ensure all players are present
    pivot = pivot.reindex(all_players, fill_value=0)

    # Ensure all matches (columns) are present
    all_columns = match_keys["Venue_Date"].tolist()
    pivot = pivot.reindex(columns=all_columns, fill_value=0)

    # Add total per player
    pivot["Total Contributed"] = pivot.sum(axis=1)

    st.dataframe(pivot.style.format("£{:.2f}"))

    # --- Net contribution per player (after expenses) ---
    st.subheader("⚖️ Net Contribution per Player (After Match Expenses)")

    # Calculate match-level net balance per player
    player_counts = payment_df.groupby(["Venue", "Date"])["Name"].nunique().reset_index()
    expenses_total = expenses_df.groupby(["Venue", "Date"])["Amount"].sum().reset_index()
    match_income = payment_df.groupby(["Venue", "Date"])["Amount"].sum().reset_index()

    merged = pd.merge(match_income, expenses_total, on=["Venue", "Date"], how="left").fillna(0)
    merged = pd.merge(merged, player_counts, on=["Venue", "Date"], how="left").fillna(1)
    merged["Venue_Date"] = merged["Venue"] + " - " + merged["Date"]

    # Adjusted code to handle renamed columns 'Amount_x' and 'Amount_y'
    if 'Amount_x' in merged.columns and 'Amount_y' in merged.columns:
        merged["Per Player Net"] = (merged["Amount_x"] - merged["Amount_y"]) / merged["Name"]
    else:
        merged["Per Player Net"] = (merged["Amount"] - merged["Amount_y"]) / merged["Name"]

    # Map per-player match net to pivot
    net_map = dict(zip(merged["Venue_Date"], merged["Per Player Net"]))
    net_contrib = pivot.copy()
    for col in all_columns:
        net = net_map.get(col, 0)
        net_contrib[col] = net

    net_contrib["Est. Player Net Total"] = net_contrib[list(all_columns)].sum(axis=1)

    st.dataframe(net_contrib.style.format("£{:.2f}"))

# --- Tab 5: Log ---
with tab5:
    st.subheader("All Player Payments")
    st.dataframe(payment_df.sort_values(by=["Date", "Venue", "Name"]))
    st.download_button("Download Payments CSV", payment_df.to_csv(index=False), "payments.csv")

    st.subheader("All Expenses")
    st.dataframe(expenses_df.sort_values(by=["Date", "Venue"]))
    st.download_button("Download Expenses CSV", expenses_df.to_csv(index=False), "expenses.csv")

    st.subheader("Other Income (Raffle, Fines)")
    st.dataframe(other_income_df.sort_values(by=["Date", "Venue"]))
    st.download_button("Download Other Income CSV", other_income_df.to_csv(index=False), "other_income.csv")
# --- Tab 6: Clear Data ---
with tab6:
    st.subheader("⚠️ Danger Zone: Clear Data")

    st.warning("Use these options carefully. Cleared data **cannot be recovered**.")

    clear_option = st.selectbox(
        "Select data to clear:",
        ["Players", "Venues", "Payments", "Expenses", "Other Income", "Balance", "Clear All"]
    )

    confirm = st.checkbox("I understand that this action is irreversible.")

    if st.button("Clear Selected Data"):
        if not confirm:
            st.error("Please confirm before clearing.")
        else:
            if clear_option == "Players":
                players_df = pd.DataFrame(columns=["Name"])
            elif clear_option == "Venues":
                venues_df = pd.DataFrame(columns=["Venue", "Date"])
            elif clear_option == "Payments":
                payment_df = pd.DataFrame(columns=["Name", "Amount", "Category", "Venue", "Date"])
            elif clear_option == "Expenses":
                expenses_df = pd.DataFrame(columns=["Venue", "Date", "Amount", "Description"])
            elif clear_option == "Other Income":
                other_income_df = pd.DataFrame(columns=["Venue", "Date", "Raffle Income", "Fines"])
            elif clear_option == "Balance":
                balance_df = pd.DataFrame(columns=["Venue", "Date", "Total Player Income", "Other Income", "Total Expenses", "Net"])
            elif clear_option == "Clear All":
                players_df = pd.DataFrame(columns=["Name"])
                venues_df = pd.DataFrame(columns=["Venue", "Date"])
                payment_df = pd.DataFrame(columns=["Name", "Amount", "Category", "Venue", "Date"])
                expenses_df = pd.DataFrame(columns=["Venue", "Date", "Amount", "Description"])
                other_income_df = pd.DataFrame(columns=["Venue", "Date", "Raffle Income", "Fines"])
                balance_df = pd.DataFrame(columns=["Venue", "Date", "Total Player Income", "Other Income", "Total Expenses", "Net"])

            save_data(balance_df, payment_df, venues_df, players_df, expenses_df, other_income_df)
            st.success(f"✅ {clear_option} data cleared.")
            st.rerun()