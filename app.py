import streamlit as st
import pandas as pd
import json

from src.schema_manager import convert_for_dataframe, delete_field, generate_schema_from_json, parse_dataframe, update_schema

st.set_page_config(page_title="🧰 Dynamic JSON Editor", layout="wide", initial_sidebar_state="collapsed")
st.title("🧾 Dynamic JSON Configuration Editor")

# Initialize session state variables
if "schemas" not in st.session_state:
    st.session_state.schemas = {
        "Default": [
            {"name": "name", "type": "string", "required": True},
            {"name": "value", "type": "string", "required": False}
        ]
    }

if "current_data" not in st.session_state:
    st.session_state.current_data = None
    
if "active_schema" not in st.session_state:
    st.session_state.active_schema = "Default"

# Sidebar Schema Control
st.sidebar.title("🛠 Schema Settings")

# Schema selection or creation
schema_names = list(st.session_state.schemas.keys())
selected_schema = st.sidebar.selectbox(
    "Choose Schema", 
    schema_names, 
    index=schema_names.index(st.session_state.active_schema) if st.session_state.active_schema in schema_names else 0
)

# Set the active schema
st.session_state.active_schema = selected_schema

# New schema creation
with st.sidebar.expander("➕ Create New Schema"):
    new_schema_name = st.text_input("New Schema Name")
    create_empty = st.radio("Schema Type", ["Empty", "Copy Current"])
    
    if st.button("Create Schema") and new_schema_name:
        if new_schema_name not in st.session_state.schemas:
            if create_empty == "Empty":
                st.session_state.schemas[new_schema_name] = []
            else:
                # Copy the current schema
                st.session_state.schemas[new_schema_name] = st.session_state.schemas[selected_schema].copy()
            
            st.session_state.active_schema = new_schema_name
            st.rerun()
        else:
            st.error(f"Schema '{new_schema_name}' already exists!")

# Access the current schema
schema = st.session_state.schemas[selected_schema]

# Schema editing section
st.sidebar.markdown("### 📝 Edit Schema")

# Field management
with st.sidebar.expander("Field Management"):
    # Add or edit field
    field_tab1, field_tab2 = st.tabs(["Add/Edit Field", "Delete Field"])
    
    with field_tab1:
        with st.form("field_form"):
            # Select existing field to edit or create new
            existing_fields = ["-- New Field --"] + [f["name"] for f in schema]
            selected_field = st.selectbox("Select Field", existing_fields)
            
            # Pre-fill values if editing existing field
            current_field = next((f for f in schema if f["name"] == selected_field), {})
            
            fname = st.text_input("Field Name", 
                                value="" if selected_field == "-- New Field --" else selected_field)
            ftype = st.selectbox("Field Type", 
                                ["string", "number", "boolean", "list"],
                                index=["string", "number", "boolean", "list"].index(current_field.get("type", "string")) 
                                if "type" in current_field else 0)
            freq = st.checkbox("Required", 
                            value=current_field.get("required", False) if current_field else False)
            fwidget = st.selectbox("Widget", 
                                ["", "textarea", "text"],
                                index=["", "textarea", "text"].index(current_field.get("widget", "")) 
                                if "widget" in current_field and current_field.get("widget") in ["", "textarea", "text"] else 0)
            
            action = "Update" if selected_field != "-- New Field --" else "Add"
            
            if st.form_submit_button(f"{action} Field") and fname:
                update_schema(st.session_state.schemas, selected_schema, fname, ftype, freq, fwidget)
                st.rerun()
    
    with field_tab2:
        remove_field = st.selectbox("Select Field to Delete", ["--"] + [f["name"] for f in schema])
        if st.button("Delete Field") and remove_field != "--":
            delete_field(st.session_state.schemas, selected_schema, remove_field)
            st.rerun()

# Upload / Import JSON
with st.expander("📥 Load JSON Data", expanded=True):
    st.markdown("### Import JSON to Create/Update Schema and Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        file = st.file_uploader("Upload JSON File", type="json")
    
    with col2:
        pasted = st.text_area("Or paste JSON", height=150)
    
    import_options = st.radio(
        "Import Options", 
        ["Update Schema & Data", "Update Data Only"]
    )
    
    if st.button("Import"):
        try:
            # Get JSON from file or pasted text
            if file:
                raw = json.load(file)
            elif pasted:
                raw = json.loads(pasted)
            else:
                st.warning("Please upload a file or paste JSON content")
                raw = None
                
            if raw:
                # Handle both list and dictionary formats
                if isinstance(raw, dict):
                    raw = [raw]  # Convert single object to list for DataFrame
                
                # Generate or update schema if requested
                if import_options == "Update Schema & Data":
                    new_schema = generate_schema_from_json(raw)
                    
                    # Check if we need to merge with existing schema
                    if schema:
                        existing_fields = {f["name"]: f for f in schema}
                        for new_field in new_schema:
                            if new_field["name"] not in existing_fields:
                                schema.append(new_field)
                    else:
                        # Just use the new schema
                        st.session_state.schemas[selected_schema] = new_schema
                
                # Convert data for DataFrame
                df_data = convert_for_dataframe(raw, st.session_state.schemas[selected_schema])
                st.session_state.current_data = pd.DataFrame(df_data)
                
                st.success("JSON data imported successfully!")
        except Exception as e:
            st.error(f"Failed to import JSON: {str(e)}")

# Initialize or update data editor columns based on schema
if selected_schema and schema:
    columns = [f["name"] for f in schema]
    
    if st.session_state.current_data is None:
        # Create new DataFrame with schema columns
        st.session_state.current_data = pd.DataFrame(columns=columns)
    else:
        # Ensure all schema columns exist in DataFrame
        for col in columns:
            if col not in st.session_state.current_data.columns:
                st.session_state.current_data[col] = ""

# ...existing code...
# Main Editor Area
st.markdown("---")
st.subheader(f"📝 Edit Data: {selected_schema}")
if schema:  # Only show editor if there are schema fields
    editor_data = st.data_editor(
        st.session_state.current_data,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_{selected_schema}"
    )
    
    # Update session state with edited data
    st.session_state.current_data = editor_data
else:
    st.info("Please import JSON or add fields to your schema.")

# Export functionality
st.markdown("---")

st.subheader("📤 Export & Save")

# Export JSON Data
st.markdown("### Export JSON Data")
if schema and not st.session_state.current_data.empty:
    try:
        final_json = parse_dataframe(st.session_state.current_data, schema)
        json_str = json.dumps(final_json, ensure_ascii=False, indent=2)
        
        export_format = st.selectbox(
            "Export Format", 
            ["JSON Array", "Single JSON Object"], 
            index=0 if len(final_json) > 1 else 1
        )
        
        if export_format == "Single JSON Object" and len(final_json) == 1:
            json_str = json.dumps(final_json[0], ensure_ascii=False, indent=2)
        
        st.code(json_str, language="json")
        st.download_button(
            "📥 Download JSON Data", 
            json_str, 
            f"{selected_schema.lower()}_data.json", 
            "application/json"
        )
    except Exception as e:
        st.error(f"Failed to export: {str(e)}")
else:
    st.info("Add schema fields and data to generate JSON output.")

# Save Schema
st.markdown("### Save Schema")
if schema:
    try:
        schema_json = json.dumps(schema, ensure_ascii=False, indent=2)
        st.code(schema_json, language="json", line_numbers=True)
        st.download_button(
            "📥 Download Schema Definition", 
            schema_json, 
            f"{selected_schema.lower()}_schema.json", 
            "application/json"
        )
    except Exception as e:
        st.error(f"Failed to export schema: {str(e)}")
else:
    st.info("Define schema fields to save your schema.")