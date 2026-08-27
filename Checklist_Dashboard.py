import streamlit as st
import gspread
import pandas as pd
import datetime
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth

# ---------------- PAGE CONFIG (must be first Streamlit command) ----------------
st.set_page_config(
    page_title="MALCO Checklist Dashboard",
    page_icon="✅",
    layout="wide"
)

# ---------------- LOGIN SETUP ----------------
credentials = {
    "usernames": {
        "mahesh": {
            "name": "Mahesh Tiwari",
            "email": "stores@malcorp.co.in",
            "password": "PASTE_HASHED_PASSWORD_HERE"
        },
        "trithankar": {
            "name": "Trithankar Maity",
            "email": "purchase@malcorp.co.in",
            "password": "PASTE_HASHED_PASSWORD_HERE"
        },
        "sanchali": {
            "name": "Sanchali Dutta Gupta",
            "email": "mis@malcorp.co.in",
            "password": "$2b$12$2j5GRWJ/KgbRTKUHIRBWX.Df7MeBC738bCQ83WHY7.YE7EW3YDtQ."
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "checklist_dashboard_cookie",
    "another_random_secret_key_456",
    cookie_expiry_days=7
)

authenticator.login()

if st.session_state["authentication_status"] is False:
    st.error("Username or password is incorrect")
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning("Please enter your username and password")
    st.stop()

name = st.session_state["name"]
username = st.session_state["username"]

authenticator.logout("Logout", "sidebar")
st.sidebar.write(f"Logged in as: **{name}**")
logged_in_email = credentials["usernames"][username]["email"]

# ---------------- GOOGLE CONNECTION (Service Account) ----------------
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

# ---------------- CSS ----------------
st.markdown("""
<style>
.dashboard-title {
    background: linear-gradient(90deg, #74b9ff 0%, #a8d8ff 100%);
    padding: 22px 28px;
    border-radius: 14px;
    margin-bottom: 25px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.15);
}
.dashboard-title h1 {
    color: white;
    margin: 0;
    font-size: 34px;
    font-weight: 800;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #eaf4ff 0%, #fdeff3 100%);
}
section[data-testid="stSidebar"] * {
    color: #2c2c3a !important;
}
.section-card {
    padding: 18px 22px;
    border-radius: 14px;
    margin-bottom: 22px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}
.section-card h2 {
    margin: 0;
    font-size: 24px;
}
.section-card p {
    margin: 4px 0 0 0;
    opacity: 0.85;
    font-size: 14px;
}
.card-tasks   { background: linear-gradient(90deg, #f5f5f0, #fff8dc); }
.card-tasks h2, .card-tasks p { color: #5c5240; }

div.stButton > button, div.stFormSubmitter > button {
    background: linear-gradient(90deg, #2575fc, #6a11cb);
    color: white;
    font-weight: 700;
    border-radius: 10px;
    border: none;
    padding: 8px 20px;
    transition: transform 0.15s ease;
}
div.stButton > button:hover, div.stFormSubmitter > button:hover {
    transform: scale(1.03);
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="dashboard-title"><h1>✅ MALCO Checklist Dashboard</h1></div>', unsafe_allow_html=True)

st_autorefresh(interval=30000, key="checklist_refresh")

now = datetime.datetime.now()

# ===================================================
# CHECKLIST PAGE
# ===================================================
checklist_sheet = client.open("Copy of MALCO_Checklist_Dashboard 26-08-2026").worksheet("Master")
checklist_data = checklist_sheet.get_all_records()
checklist_df = pd.DataFrame(checklist_data)

st.markdown("""
<div class="section-card card-tasks">
    <h2>✅ Checklist</h2>
    <p>Your recurring compliance & operational tasks</p>
</div>
""", unsafe_allow_html=True)

st.caption("If you mark a task as complete, it will disappear from this list after 5 minutes.")

# Normalize blank Status to "Pending"
checklist_df["Status"] = checklist_df["Status"].replace("", "Pending").fillna("Pending")

# Filter to only this doer's rows
my_checklist_full = checklist_df[
    checklist_df["Email"].str.lower() == logged_in_email.lower()
].reset_index(drop=False)

# ---------------- Guard: no rows for this doer at all ----------------
if my_checklist_full.empty:
    st.warning(f"No checklist tasks found for your email ({logged_in_email}) in the Master sheet.")
    st.stop()

# ---------------- Show logic ----------------
CHECKLIST_HIDE_AFTER_MINUTES = 5

def should_show_checklist(row):
    actual = str(row["Actual"]).strip()

    # Blank Actual -> genuinely pending -> always show
    if not actual or actual.lower() == "nan":
        return True

    # Actual has a date -> task is Done
    # If it was JUST marked done (has a full timestamp), apply 5-min hide
    try:
        done_time = datetime.datetime.strptime(actual, "%d-%m-%Y %H:%M:%S")
        elapsed = (now - done_time).total_seconds() / 60
        return elapsed < CHECKLIST_HIDE_AFTER_MINUTES
    except:
        # Actual is a plain historical date (dd-mm-yyyy only) -> already done, hide it
        return False

my_checklist_visible = my_checklist_full[my_checklist_full.apply(should_show_checklist, axis=1)].reset_index(drop=True)

# ---------------- FILTERS ----------------
if not my_checklist_visible.empty:
    task_options = ["All"] + sorted(my_checklist_visible["Task"].dropna().unique().tolist())
    freq_options = ["All"] + sorted(my_checklist_visible["Freq"].dropna().unique().tolist())
else:
    task_options = ["All"]
    freq_options = ["All"]
status_options = ["All", "Pending", "Done"]

f1, f2, f3 = st.columns(3)
with f1:
    filter_task = st.selectbox("🔍 Filter by Task", task_options, key="filter_task_checklist")
with f2:
    filter_freq = st.selectbox("🔍 Filter by Frequency", freq_options, key="filter_freq_checklist")
with f3:
    filter_status_cl = st.selectbox("🔍 Filter by Status", status_options, key="filter_status_checklist")

if not my_checklist_visible.empty:
    if filter_task != "All":
        my_checklist_visible = my_checklist_visible[my_checklist_visible["Task"] == filter_task]
    if filter_freq != "All":
        my_checklist_visible = my_checklist_visible[my_checklist_visible["Freq"] == filter_freq]
    if filter_status_cl != "All":
        my_checklist_visible = my_checklist_visible[my_checklist_visible["Status"] == filter_status_cl]
    my_checklist_visible = my_checklist_visible.reset_index(drop=True)

# ---------------- DISPLAY & EDIT ----------------
checklist_display_cols = ["Task ID", "Task", "Freq", "Planned", "Actual", "Status"]

if my_checklist_visible.empty:
    st.info("No checklist tasks to show right now.")
else:
    edited_checklist = st.data_editor(
        my_checklist_visible[checklist_display_cols],
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["Pending", "Done"],
                required=True
            ),
            "Actual": st.column_config.Column("Actual", disabled=True),
            "Planned": st.column_config.Column("Planned", disabled=True)
        },
        disabled=[c for c in checklist_display_cols if c != "Status"],
        hide_index=True,
        key="editor_checklist"
    )

    if st.button("💾 Save Checklist Changes", key="save_checklist"):
        status_col = checklist_df.columns.get_loc("Status") + 1
        actual_col = checklist_df.columns.get_loc("Actual") + 1
        updates = 0

        for i in range(len(my_checklist_visible)):
            old_status = my_checklist_visible.at[i, "Status"]
            new_status = edited_checklist.at[i, "Status"]

            if old_status != new_status:
                original_row_index = my_checklist_visible.at[i, "index"]
                row_number = original_row_index + 2  # header is row 1, data starts row 2

                checklist_sheet.update_cell(row_number, status_col, new_status)

                if new_status == "Done":
                    now_str = now.strftime("%d-%m-%Y %H:%M:%S")
                    checklist_sheet.update_cell(row_number, actual_col, now_str)
                updates += 1

        if updates > 0:
            st.success(f"✅ Saved {updates} change(s)!")
            st.rerun()
        else:
            st.info("No changes to save.")