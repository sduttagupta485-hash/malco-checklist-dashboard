import streamlit as st
import gspread
import pandas as pd
import datetime
import hmac
import hashlib
import base64
import time
import json
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh
import streamlit_authenticator as stauth

# ---------------- PAGE CONFIG (must be first Streamlit command) ----------------
st.set_page_config(
    page_title="MALCO Checklist Dashboard",
    page_icon="✅",
    layout="wide"
)

# ============================================================
# GOOGLE SHEET CONFIG — change these 2 lines if the sheet or
# tab name ever changes. Nothing else needs to be touched, and
# the portal will automatically show whatever this app shows —
# no changes needed on the portal side.
# ============================================================
SHEET_NAME = "Copy of MALCO_Checklist_Dashboard 26-08-2026"
WORKSHEET_NAME = "Master"
# ============================================================

# ---------------- LOGIN SETUP ----------------
credentials = {
    "usernames": {
        "mahesh": {
            "name": "Mahesh Tiwari",
            "email": "stores@malcorp.co.in",
            "password": "$2b$12$sTAQvUOsJf0icXVuHTPLhOToBdo1n7/PIXo/28fveZ4ihYHlAqq.S",
            "role": "doer"
        },
        "trithankar": {
            "name": "Trithankar Maity",
            "email": "purchase@malcorp.co.in",
            "password": "$2b$12$I.KHmaSCpIU1l45IxiOgy.gkZhLUt98c94xzhET8vxNVGubcHDBBy",
            "role": "doer"
        },
        "priyanka": {
            "name": "Priyanka Chakraborty",
            "email": "hr@malcorp.co.in",
            "password": "$2b$12$GP3CC2FXdUpBydjC6/MN7et/o5Piy5RZdFpJ77xvotoevlajX2vIm",
            "role": "doer"
        },
        "vikesh": {
            "name": "Vikesh Singh",
            "email": "accounts@malcorp.co.in",
            "password": "$2b$12$IcEYzLSFUmWNPowfiIH/zugD0.9XsKR8I72F74wTzST0/PmF9nbVG",
            "role": "doer"
        },
        "pankaj": {
            "name": "Pankaj Kumar Jha",
            "email": "accounts@malcorp.co.in",
            "password": "$2b$12$JqZK4Xo1POtazDv1uDqh.upVGLYKVFrYOqSM/.Kl48w35//vomIyC",
            "role": "doer"
        },
        "govind": {
            "name": "Govind Prasad",
            "email": "taxation@malcoindia.co.in",
            "password": "$2b$12$2jNvcP3Y89vvjjB3Mhr5H.YdEUJT9Zvjzfu.dWe/RYuFfTbbykmY6",
            "role": "doer"
        },
        "ved": {
            "name": "Ved Byas",
            "email": "accounts@malcorp.co.in",
            "password": "$2b$12$Kac4rQF041LeGj2egmMGJeQ3QYVGAJVmTYxH8mhMeb5aoDE7ot5D",
            "role": "doer"
        },
        "sanchali": {
            "name": "Sanchali Dutta Gupta",
            "email": "mis@malcorp.co.in",
            "employee_id": " A3069",
            "password": "$2b$12$goj3e3beDIEuuCPb1oUqnubwuS69fse1Wxg9kUMFZKvH6MJXE.K/G",
            "role": "doer"
        },
        "sanchita": {
            "name": "Sanchita Dewan Mukherjee",
            "email": "pc@malcorp.co.in",
            "password": "$2b$12$z.gzhRtlJiHmO4WPbX7q9ekrqH.9aQSSwccNPdqJ7l5Xt6oFDmV/e",
            "role": "pc"
        },
        "md_admin": {
            "name": "Managing Director",
            "email": "md@malcorp.co.in",
            "password": "$2b$12$qS1HExtmuZI/ibJpSCdhI.Ti4IjkOUTJtzrL8oFPrYY09G4t1NECS",
            "role": "md"
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "checklist_dashboard_cookie",
    "another_random_secret_key_456",
    cookie_expiry_days=7
)

# =====================================================================
# SSO: verify a signed token passed from the HTML portal (?token=...)
# =====================================================================
def verify_sso_token(token, secret):
    try:
        payload_b64, signature = token.split(".")
        expected_sig = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None  # tampered or forged

        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))

        if payload["expires"] < time.time():
            return None  # expired

        return payload["email"]
    except Exception:
        return None

sso_email = None
if "sso_secret" in st.secrets:
    query_params = st.query_params
    sso_token = query_params.get("token")
    if sso_token:
        sso_email = verify_sso_token(sso_token, st.secrets["sso_secret"])

# ---------------- LOGIN: SSO first, normal login as fallback ----------------
if sso_email:
    matched_username = None
    for uname, info in credentials["usernames"].items():
        if info["email"].lower() == sso_email.lower():
            matched_username = uname
            break

    if matched_username is None:
        st.error(f"Your account ({sso_email}) was not recognized. Please contact MIS.")
        st.stop()

    name = credentials["usernames"][matched_username]["name"]
    username = matched_username
    logged_in_email = credentials["usernames"][matched_username]["email"]
    logged_in_role = credentials["usernames"][matched_username].get("role", "doer")
    st.sidebar.write(f"Logged in as: **{name}** (via portal)")

else:
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
    logged_in_role = credentials["usernames"][username].get("role", "doer")

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

# ---------------- DYNAMIC TITLE BASED ON ROLE ----------------
if logged_in_role == "pc":
    dashboard_title_text = "🏭 MALCO_PC Checklist Dashboard"
elif logged_in_role == "md":
    dashboard_title_text = "🏭 MALCO_MD Checklist Dashboard"
else:
    dashboard_title_text = "✅ MALCO Checklist Dashboard"

st.markdown(f'<div class="dashboard-title"><h1>{dashboard_title_text}</h1></div>', unsafe_allow_html=True)

st_autorefresh(interval=30000, key="checklist_refresh")

now = datetime.datetime.now()

# ===================================================
# CHECKLIST PAGE
# ===================================================
checklist_sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
checklist_data = checklist_sheet.get_all_records()
checklist_df = pd.DataFrame(checklist_data)

st.markdown("""
<div class="section-card card-tasks">
    <h2>✅ Checklist</h2>
    <p>Your recurring compliance & operational tasks</p>
</div>
""", unsafe_allow_html=True)

# Normalize blank Status to "Pending"
checklist_df["Status"] = checklist_df["Status"].replace("", "Pending").fillna("Pending")

# ---------------- Show logic for DOER "Done" auto-hide ----------------
CHECKLIST_HIDE_AFTER_MINUTES = 5

def should_show_checklist(row):
    actual = str(row["Actual"]).strip()
    if not actual or actual.lower() == "nan":
        return True
    try:
        done_time = datetime.datetime.strptime(actual, "%d-%m-%Y %H:%M:%S")
        elapsed = (now - done_time).total_seconds() / 60
        return elapsed < CHECKLIST_HIDE_AFTER_MINUTES
    except:
        return False

# =====================================================================
# BRANCH: PC / MD (all doers, follow-up view) vs DOER (own tasks only)
# =====================================================================
if logged_in_role in ("pc", "md"):
    st.info(f"👁️ Viewing as **{logged_in_role.upper()}** — showing all doers' tasks for follow-up")

    my_checklist_full = checklist_df.reset_index(drop=False)

    show_only_pending = st.checkbox("🔴 Show only Pending tasks (for follow-up)", value=True)
    if show_only_pending:
        my_checklist_visible = my_checklist_full[my_checklist_full["Status"] == "Pending"].reset_index(drop=True)
    else:
        my_checklist_visible = my_checklist_full.reset_index(drop=True)

    # ---------------- FILTERS ----------------
    name_options = ["All"] + sorted(my_checklist_visible["Name"].dropna().unique().tolist())
    dept_options = ["All"] + sorted(my_checklist_visible["Department"].dropna().unique().tolist())
    task_options = ["All"] + sorted(my_checklist_visible["Task"].dropna().unique().tolist())

    f1, f2, f3 = st.columns(3)
    with f1:
        filter_name = st.selectbox("🔍 Filter by Doer", name_options, key="filter_name_pcmd")
    with f2:
        filter_dept = st.selectbox("🔍 Filter by Department", dept_options, key="filter_dept_pcmd")
    with f3:
        filter_task_pcmd = st.selectbox("🔍 Filter by Task", task_options, key="filter_task_pcmd")

    if filter_name != "All":
        my_checklist_visible = my_checklist_visible[my_checklist_visible["Name"] == filter_name]
    if filter_dept != "All":
        my_checklist_visible = my_checklist_visible[my_checklist_visible["Department"] == filter_dept]
    if filter_task_pcmd != "All":
        my_checklist_visible = my_checklist_visible[my_checklist_visible["Task"] == filter_task_pcmd]
    my_checklist_visible = my_checklist_visible.reset_index(drop=True)

    checklist_display_cols = ["Name", "Email", "Department", "Task ID", "Task", "Freq", "Planned", "Actual", "Status"]

    st.write(f"**{len(my_checklist_visible)} task(s) found**")

    if my_checklist_visible.empty:
        st.info("No tasks match the current filters.")
    else:
        st.dataframe(my_checklist_visible[checklist_display_cols], hide_index=True)

else:
    # ---------------- DOER VIEW (existing behavior) ----------------
    st.caption("If you mark a task as complete, it will disappear from this list after 5 minutes.")

    my_checklist_full = checklist_df[
        checklist_df["Email"].str.lower() == logged_in_email.lower()
    ].reset_index(drop=False)

    if my_checklist_full.empty:
        st.warning(f"No checklist tasks found for your email ({logged_in_email}) in the Master sheet.")
        st.stop()

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
                    row_number = original_row_index + 2

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
