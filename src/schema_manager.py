# Helper Functions
from typing import Dict, List, Any, Optional, Union
import pandas as pd


def guess_field_type(value: Any) -> str:
    """Determine the type of a field based on its value"""
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, list):
        return "list"
    else:
        return "string"

def generate_schema_from_json(data: Union[List[Dict], Dict]) -> List[Dict]:
    """Automatically generate a schema from JSON data"""
    if isinstance(data, dict):
        # Single JSON object
        sample_object = data
    elif isinstance(data, list) and len(data) > 0:
        # List of JSON objects, use the first one as a template
        sample_object = data[0]
    else:
        # Empty or invalid data
        return []
    
    schema = []
    for key, value in sample_object.items():
        field_type = guess_field_type(value)
        # Suggest a widget based on the field type and value
        widget = ""
        if field_type == "string" and isinstance(value, str) and len(value) > 50:
            widget = "textarea"
        
        schema.append({
            "name": key,
            "type": field_type,
            "required": False,  # Default to non-required
            "widget": widget
        })
    
    return schema

def update_schema(schemas: Dict, schema_name: str, field_name: str, field_type: str, 
                 required: bool = False, widget: Optional[str] = None) -> None:
    """Add or update a field in a schema"""
    field = {"name": field_name, "type": field_type, "required": required}
    if widget and widget != "":
        field["widget"] = widget
    
    # Check if field already exists
    for i, existing_field in enumerate(schemas[schema_name]):
        if existing_field["name"] == field_name:
            schemas[schema_name][i] = field
            return
    
    # If not found, add new field
    schemas[schema_name].append(field)

def delete_field(schemas: Dict, schema_name: str, field_name: str) -> None:
    """Remove a field from a schema"""
    schemas[schema_name] = [f for f in schemas[schema_name] if f["name"] != field_name]

def convert_for_dataframe(data: List[Dict], schema: List[Dict]) -> List[Dict]:
    """Convert JSON data to a format suitable for DataFrame"""
    result = []
    
    # Create a mapping of field names to types
    field_types = {f["name"]: f["type"] for f in schema}
    
    for item in data:
        converted_item = {}
        for key, value in item.items():
            # Convert list fields to comma-separated strings for DataFrame
            if key in field_types and field_types[key] == "list" and isinstance(value, list):
                converted_item[key] = ", ".join(str(v) for v in value)
            else:
                converted_item[key] = value
        result.append(converted_item)
    
    return result

def parse_dataframe(df: pd.DataFrame, schema: List[Dict]) -> List[Dict]:
    """Convert DataFrame back to JSON format"""
    parsed = []
    
    for _, row in df.iterrows():
        # Skip empty rows
        if row.isnull().all() or (row.astype(str).str.strip() == '').all():
            continue
            
        record = {}
        for field in schema:
            name = field["name"]
            val = row.get(name, "")
            
            # Handle different field types
            if pd.isna(val) or str(val).strip() == '':
                if field["type"] == "list":
                    record[name] = []
                elif field["type"] == "number":
                    record[name] = 0
                elif field["type"] == "boolean":
                    record[name] = False
                else:
                    record[name] = ""
            else:
                if field["type"] == "list":
                    record[name] = [v.strip() for v in str(val).split(",") if v.strip()]
                elif field["type"] == "number":
                    try:
                        record[name] = float(val)
                        # Convert to int if it's a whole number
                        if record[name] == int(record[name]):
                            record[name] = int(record[name])
                    except:
                        record[name] = 0
                elif field["type"] == "boolean":
                    if isinstance(val, bool):
                        record[name] = val
                    else:
                        lower_val = str(val).lower()
                        record[name] = lower_val in ['true', 'yes', '1', 'y']
                else:
                    record[name] = str(val)
        
        parsed.append(record)
    return parsed