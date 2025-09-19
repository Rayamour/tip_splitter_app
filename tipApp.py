import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import json

DATA_PATH = "tips_data.json"

def load_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)
        # Convert to DataFrame and expand names into columns
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    else:
        return pd.DataFrame(columns=["date", "total_tip", "per_person_share"])

def save_data(df):
    # Convert DataFrame back to list of dicts for JSON storage
    data = []
    for _, row in df.iterrows():
        record = {"date": row['date'].isoformat(), "total_tip": row['total_tip'], "per_person_share": row['per_person_share']}
        # Add name columns (skip date, total_tip, per_person_share)
        for col in row.index:
            if col not in ['date', 'total_tip', 'per_person_share']:
                if pd.notna(row[col]):
                    record[col] = row[col]
        data.append(record)
    
    with open(DATA_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def get_name_columns(df):
    """Get all unique name columns from the dataframe"""
    name_cols = []
    for col in df.columns:
        if col not in ['date', 'total_tip', 'per_person_share']:
            name_cols.append(col)
    return name_cols

def calculate_tip_per_person(total_tip, num_people):
    return round(total_tip / num_people, 2) if num_people > 0 else 0.0

def delete_name(df, name_to_delete):
    """Delete a name column from the dataframe"""
    if name_to_delete in df.columns:
        df = df.drop(columns=[name_to_delete])
    return df

def format_date_for_display(date_value):
    """Safely format date for display"""
    if pd.isna(date_value):
        return ""
    elif isinstance(date_value, (date, pd.Timestamp)):
        return date_value.strftime('%Y-%m-%d')
    else:
        return str(date_value)

st.set_page_config(page_title="Tip Splitter", layout="centered")

st.title("Tip Splitter App")
st.write(
    "Enter the names of people who worked each day and the total tip. "
    "The app creates columns for each person and calculates equal shares."
)

# --- Daily entry ---
st.header("Daily Tip Entry")
col1, col2 = st.columns(2)

with col1:
    entry_date = st.date_input("Date", value=date.today())
    
    # Get existing names for dropdown
    df = load_data()
    existing_names = get_name_columns(df) if not df.empty else []
    
    # Name management
    st.subheader("People")
    new_names_input = st.text_input(
        "Add new names (comma-separated)",
        placeholder="Enter new names: Ahmed, Fatima"
    )
    
    # Show existing names as checkboxes
    selected_names = []
    if existing_names:
        st.write("**Select existing people:**")
        for name in existing_names:
            if st.checkbox(name, key=f"select_{name}"):
                selected_names.append(name)
    
    # Add new names
    if new_names_input:
        new_names = [n.strip() for n in new_names_input.split(",") if n.strip()]
        for name in new_names:
            if name not in existing_names:
                if st.checkbox(f"Add: {name}", key=f"add_{name}"):
                    selected_names.append(name)

with col2:
    total_tip = st.number_input("Total Tip (your currency)", min_value=0.0, step=0.5, format="%.2f")
    
    # Show calculation preview
    if selected_names:
        num_people = len(selected_names)
        per_share = calculate_tip_per_person(total_tip, num_people)
        st.info(f"**{num_people} people selected** — Each gets: **{per_share}**")
    
    add_new = st.button("Save This Day", type="primary")

# Handle new entry
if add_new:
    if not selected_names:
        st.error("Please select or add at least one person")
    elif total_tip <= 0:
        st.error("Please enter a valid tip amount")
    else:
        num_people = len(selected_names)
        per_share = calculate_tip_per_person(total_tip, num_people)
        
        # Create new row properly
        new_row = pd.DataFrame(index=[0])
        new_row['date'] = entry_date
        new_row['total_tip'] = total_tip
        new_row['per_person_share'] = per_share
        
        # Add selected names as columns
        for name in selected_names:
            new_row[name] = per_share
        
        # Load existing data and append
        df = load_data()
        if not df.empty:
            # Align columns with existing dataframe
            for col in df.columns:
                if col not in new_row.columns and col not in ['date', 'total_tip', 'per_person_share']:
                    new_row[col] = 0.0
            
            for col in new_row.columns:
                if col not in df.columns and col not in ['date', 'total_tip', 'per_person_share']:
                    df[col] = 0.0
            
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            # For empty dataframe, set proper columns
            all_columns = ['date', 'total_tip', 'per_person_share'] + selected_names
            df = pd.DataFrame(columns=all_columns)
            df = pd.concat([df, new_row], ignore_index=True)
            
        # Reorder columns to have date first, then names, then summary columns
        name_cols = get_name_columns(df)
        cols_order = ['date'] + name_cols + ['total_tip', 'per_person_share']
        existing_cols = [col for col in cols_order if col in df.columns]
        df = df[existing_cols]
        
        save_data(df)
        st.success(f"✅ Saved! {num_people} people — each gets {per_share}")
        st.experimental_rerun()

# --- Edit functionality ---
st.header("Edit Records")

df = load_data()
if df.empty:
    st.info("No records yet.")
else:
    # Show all records with edit/delete options
    st.subheader("All Records")
    name_columns = get_name_columns(df)
    
    for idx, row in df.iterrows():
        with st.expander(f"📅 {format_date_for_display(row['date'])} - Total: {row['total_tip']} ({len([c for c in name_columns if pd.notna(row[c]) and row[c] > 0])} people)"):
            col_edit, col_delete = st.columns([3, 1])
            
            with col_edit:
                st.write("**People present:**")
                people_present = []
                for name in name_columns:
                    if pd.notna(row[name]) and row[name] > 0:
                        people_present.append(name)
                
                edited_people = st.multiselect(
                    "Select people who were present",
                    options=name_columns,
                    default=people_present,
                    key=f"edit_people_{idx}"
                )
                
                edited_tip = st.number_input(
                    "Total tip amount",
                    value=float(row['total_tip']),
                    min_value=0.0,
                    step=0.5,
                    key=f"edit_tip_{idx}",
                    format="%.2f"
                )
                
                if st.button(f"Update Record {format_date_for_display(row['date'])}", key=f"update_{idx}"):
                    if edited_people:
                        num_people = len(edited_people)
                        per_share = calculate_tip_per_person(edited_tip, num_people)
                        
                        # Update the row
                        for name in name_columns:
                            if name in edited_people:
                                df.at[idx, name] = per_share
                            else:
                                df.at[idx, name] = 0.0
                        
                        df.at[idx, 'total_tip'] = edited_tip
                        df.at[idx, 'per_person_share'] = per_share
                        
                        save_data(df)
                        st.success(f"Updated {format_date_for_display(row['date'])}! Each gets {per_share}")
                        st.experimental_rerun()
            
            with col_delete:
                if st.button("🗑️ Delete", key=f"delete_{idx}"):
                    df = df.drop(idx).reset_index(drop=True)
                    save_data(df)
                    st.success(f"Deleted record for {format_date_for_display(row['date'])}")
                    st.experimental_rerun()

    # --- Show summary table ---
    st.header("Summary Table")
    display_df = df.copy()
    
    # FIXED: Safe date formatting without .dt accessor
    display_df['date'] = display_df['date'].apply(format_date_for_display)
    
    # Only show relevant columns (date, names with values > 0, total_tip, per_person_share)
    relevant_cols = ['date', 'total_tip', 'per_person_share']
    for name in name_columns:
        if (display_df[name] > 0).any():
            relevant_cols.insert(1, name)
    
    st.dataframe(display_df[relevant_cols], use_container_width=True)

    # --- 30-day summary ---
    st.header("30-Day Summary (last 30 days)")
    end = date.today()
    start = end - timedelta(days=29)
    
    # Create long format for summary
    summary_data = []
    for _, row in df.iterrows():
        row_date = row['date']
        
        # FIXED: Safe date comparison
        if isinstance(row_date, (date, pd.Timestamp)):
            row_date = row_date.date() if hasattr(row_date, 'date') else row_date
        
        if isinstance(row_date, date) and start <= row_date <= end:
            for name in name_columns:
                if pd.notna(row[name]) and row[name] > 0:
                    summary_data.append({
                        'date': row_date,
                        'name': name,
                        'amount': row[name]
                    })
    
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        person_totals = summary_df.groupby('name')['amount'].sum().sort_values(ascending=False)
        person_totals = person_totals.reset_index()
        person_totals.columns = ['name', 'total_received_in_last_30_days']
        
        st.subheader(f"From {start} to {end} — totals per person")
        st.dataframe(person_totals, use_container_width=True)
    else:
        st.info(f"No records from {start} to {end}.")

    # --- Full time summary ---
    if st.button("Show Full Time Summary"):
        full_summary_data = []
        for _, row in df.iterrows():
            for name in name_columns:
                if pd.notna(row[name]) and row[name] > 0:
                    full_summary_data.append({
                        'name': name,
                        'amount': row[name]
                    })
        
        if full_summary_data:
            full_df = pd.DataFrame(full_summary_data)
            total_summary = full_df.groupby('name')['amount'].sum().sort_values(ascending=False)
            total_summary = total_summary.reset_index()
            total_summary.columns = ['name', 'total_received_all_time']
            
            st.subheader("All Time Totals")
            st.dataframe(total_summary, use_container_width=True)

# --- Extra options ---
st.header("More Options")
colA, colB = st.columns(2)

with colA:
    if st.button("📊 Export All Data to CSV"):
        if not df.empty:
            export_df = df.copy()
            # FIXED: Safe date formatting for export
            export_df['date'] = export_df['date'].apply(format_date_for_display)
            export_df.to_csv("tips_full_data.csv", index=False)
            st.success("✅ Exported to tips_full_data.csv")
        else:
            st.info("No data to export.")

with colB:
    if st.button("🗑️ Delete All Data (Caution!)"):
        if os.path.exists(DATA_PATH):
            os.remove(DATA_PATH)
            st.success("🗑️ All data deleted!")
            #st.experimental_rerun()
        else:
            st.info("No data to delete.")

# --- Name Management ---
st.header("Manage Names")
st.write("You can add new names through the daily entry form above. All names will automatically become columns.")

existing_names = get_name_columns(load_data()) if not load_data().empty else []
if existing_names:
    st.write(f"**Current people (columns):** {', '.join(existing_names)}")
    
    # Add delete name functionality
    st.subheader("Delete Names")
    st.warning("⚠️ Deleting a name will remove that column from ALL records")
    
    col_delete1, col_delete2 = st.columns(2)
    
    for i, name in enumerate(existing_names):
        col = col_delete1 if i % 2 == 0 else col_delete2
        with col:
            if st.button(f"🗑️ Delete {name}", key=f"delete_name_{name}"):
                df = load_data()
                df = delete_name(df, name)
                save_data(df)
                st.success(f"Deleted name: {name}")
                st.experimental_rerun()
else:
    st.info("No names added yet.")