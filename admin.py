import streamlit as st
from supabase import create_client
import time

# ── Hardcoded credentials ──────────────────────────────────────────
SUPABASE_URL = "https://dkwojxzwtzxhzszpilas.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRrd29qeHp3dHp4aHpzenBpbGFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI2Mzg0NzQsImV4cCI6MjA4ODIxNDQ3NH0.DpCuFfBtH2-8tlX10lshel0JMpJOKGn00aYPzuYStog"


if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = 0
    
# ── Page config ────────────────────────────────────────────────────
st.set_page_config(page_title="Admin Dashboard", page_icon="🛠️", layout="wide")
st.title("🛠️ Admin Dashboard — Lab Equipment")

# ── Init connection ────────────────────────────────────────────────
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

def fetch_equipment():
    return supabase.table("lab_equipment").select("*").order("lab_type").execute().data


# ── Session state for message ──────────────────────────────────────
if "admin_message" not in st.session_state:
    st.session_state.admin_message = None
    st.session_state.admin_message_type = None

# ── Auto refresh every 5 seconds ──────────────────────────────────
@st.fragment(run_every=5)
def live_dashboard():
    data = fetch_equipment()

    total      = len(data)
    faulty     = [r for r in data if r["is_faulty"] == "Yes"]
    working    = [r for r in data if r["is_faulty"] == "No"]
    chem_fault = [r for r in faulty if r["lab_type"] == "Chemistry"]
    phy_fault  = [r for r in faulty if r["lab_type"] == "Physics"]

    st.caption("🔄 Auto-refreshing every 5 seconds")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Equipment",  total)
    col2.metric("✅ Working",        len(working))
    col3.metric("🚨 Faulty",         len(faulty))
    col4.metric("⚗️ Chem Faulty",    len(chem_fault))
    col5.metric("⚡ Physics Faulty", len(phy_fault))

    st.divider()

    tab1, tab2 = st.tabs(["🚨 Faulty Equipment", "📋 All Equipment"])

    with tab1:
        st.subheader("🚨 Faulty Equipment Only")
        if not faulty:
            st.success("🎉 No faulty equipment right now!")
        else:
            for row in faulty:
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.write(f"**{row['equipment_name']}**")
                c2.write(row["lab_type"])
                c3.write(row["serial_number"])

    with tab2:
        st.subheader("All Equipment")
        lab_filter = st.radio("Filter by Lab", ["All", "Chemistry", "Physics"], horizontal=True, key="tab1_filter")
        filtered = data if lab_filter == "All" else [r for r in data if r["lab_type"] == lab_filter]
        for row in filtered:
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.write(f"**{row['equipment_name']}**")
            c2.write(row["lab_type"])
            c3.write(row["serial_number"])
            if row["is_faulty"] == "Yes":
                c4.error("🚨 Faulty")
            else:
                c4.success("✅ Working")

# ── Live dashboard renders here (auto-refreshes quietly) ──────────
live_dashboard()

st.divider()

# ══════════════════════════════════════════════════════════════════
# Update section stays outside fragment (no auto-refresh needed)
# ══════════════════════════════════════════════════════════════════
st.subheader("✏️ Update Equipment Status")

data2 = fetch_equipment()
lab_filter2   = st.radio("Filter by Lab", ["All", "Chemistry", "Physics"], horizontal=True, key="tab3_filter")
filtered2     = data2 if lab_filter2 == "All" else [r for r in data2 if r["lab_type"] == lab_filter2]
equipment_options = [f"{r['equipment_name']}  |  {r['lab_type']}  |  Serial: {r['serial_number']}" for r in filtered2]
equipment_map     = {f"{r['equipment_name']}  |  {r['lab_type']}  |  Serial: {r['serial_number']}": r for r in filtered2}

if "admin_selected" not in st.session_state:
    st.session_state.admin_selected = None

default_index = 0
if st.session_state.admin_selected in equipment_options:
    default_index = equipment_options.index(st.session_state.admin_selected)

selected = st.selectbox("Select Equipment", equipment_options, index=default_index)
st.session_state.admin_selected = selected

if selected:
    row = equipment_map[selected]
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Equipment",     row["equipment_name"])
    c2.metric("Lab",           row["lab_type"])
    c3.metric("Serial Number", row["serial_number"])

    if row["is_faulty"] == "Yes":
        st.error("⚠️ Current Status: **FAULTY**")
    else:
        st.success("✅ Current Status: **Working Fine**")

    new_status_label = st.radio(
        "Is the Equipment working properly?",
        ["Yes", "No"],
        index=0 if row["is_faulty"] == "No" else 1,
        horizontal=True,
        key="admin_radio"
    )
    new_faulty_value = "No" if new_status_label == "Yes" else "Yes"

    if st.button("💾 Save Change", use_container_width=True):
        if new_faulty_value == row["is_faulty"]:
            st.session_state.admin_message      = "⚠️ Status is already set to that value. No change made."
            st.session_state.admin_message_type = "warning"
        else:
            supabase.table("lab_equipment") \
                .update({"is_faulty": new_faulty_value}) \
                .eq("id", row["id"]) \
                .execute()
            if new_faulty_value == "Yes":
                st.session_state.admin_message      = f"🚨 **{row['equipment_name']}** marked as **FAULTY**"
                st.session_state.admin_message_type = "error"
            else:
                st.session_state.admin_message      = f"✅ **{row['equipment_name']}** marked as **Working Fine**"
                st.session_state.admin_message_type = "success"
            st.cache_data.clear()
            st.rerun()

    if st.session_state.admin_message:
        if st.session_state.admin_message_type == "error":
            st.error(st.session_state.admin_message)
        elif st.session_state.admin_message_type == "success":
            st.success(st.session_state.admin_message)
        elif st.session_state.admin_message_type == "warning":
            st.warning(st.session_state.admin_message)