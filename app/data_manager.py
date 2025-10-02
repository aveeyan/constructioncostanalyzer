import json
import os
import uuid
import csv

# --- File Path Constants ---
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DATA_FILE = os.path.join(DATA_DIR, 'data.json')

# ======================================================================================
# CORE DATA HELPERS (JSON for Projects/Categories, CSV for Master Inventory)
# ======================================================================================

def _load_json_data():
    """Loads the main data file (data.json) for projects and categories."""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return a default structure if the file is missing or corrupt
        return {"categories": [], "projects": []}

def _save_json_data(data):
    """Saves the provided data dictionary to data.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def _load_master_csv(item_type):
    """
    Loads and standardizes master data from a CSV file (e.g., labor.csv).
    This function now ensures every item has a consistent 'id' key.
    """
    file_path = os.path.join(DATA_DIR, f'{item_type}.csv')
    data = []
    try:
        with open(file_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # --- Data Integrity Layer ---
                # Ensure 'id' exists, using 'SerialNo' as the canonical ID.
                # This is critical for the frontend interaction model.
                if 'SerialNo' in row:
                    row['id'] = row['SerialNo']
                else:
                    # Fallback for data missing a SerialNo, though this indicates a schema issue.
                    row['id'] = str(uuid.uuid4())
                
                # Ensure Price is a float
                row['Price'] = float(row.get('Price', 0.0))
                
                # Standardize the inconsistent 'Type' key (e.g., 'LaborType') to 'name'
                type_key = f"{item_type.capitalize()}Type"
                if type_key in row:
                    row['name'] = row.pop(type_key)
                elif 'Type' in row: # Fallback
                     row['name'] = row.pop('Type')

                data.append(row)
    except FileNotFoundError:
        print(f"Warning: Master data file not found at {file_path}. A new one will be created on save.")
    return data

def _save_master_csv(item_type, data):
    """Saves a list of dictionaries back to the appropriate CSV file."""
    file_path = os.path.join(DATA_DIR, f'{item_type}.csv')
    os.makedirs(DATA_DIR, exist_ok=True)

    if not data:
        # If all data is deleted, write an empty file with headers.
        headers = ['SerialNo', f'{item_type.capitalize()}Type', 'Unit', 'Price']
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        return

    # Dynamically determine headers from the first data item, ensuring canonical order.
    # We must reverse the 'name' standardization for writing.
    type_key = f"{item_type.capitalize()}Type"
    headers = ['SerialNo', type_key, 'Unit', 'Price']
    
    with open(file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            # Prepare row for writing by mapping internal keys back to CSV headers
            write_row = {
                'SerialNo': row.get('id'),
                type_key: row.get('name'),
                'Unit': row.get('Unit'),
                'Price': row.get('Price')
            }
            writer.writerow(write_row)

# ======================================================================================
# MASTER INVENTORY CRUD (OPERATES ON CSV)
# ======================================================================================

def get_master_data(item_type):
    """Public function to get master data. This is the single source of truth."""
    return _load_master_csv(item_type)

def add_master_item(item_type, data):
    """Adds a new item to the master inventory CSV."""
    all_items = _load_master_csv(item_type)
    
    # Generate a new unique SerialNo/ID
    max_id = 0
    for item in all_items:
        try:
            max_id = max(max_id, int(item.get('id', 0)))
        except (ValueError, TypeError):
            continue # Skip non-integer IDs
    new_id = str(max_id + 1)

    new_item = {
        'id': new_id,
        'name': data['name'],
        'Unit': data['unit'],
        'Price': data['price']
    }
    all_items.append(new_item)
    _save_master_csv(item_type, all_items)

def update_master_item(item_type, item_id, data):
    """Updates an existing item in the master inventory CSV."""
    all_items = _load_master_csv(item_type)
    for item in all_items:
        if item.get('id') == item_id:
            item['name'] = data['name']
            item['Unit'] = data['unit']
            item['Price'] = data['price']
            break
    _save_master_csv(item_type, all_items)

def delete_master_item(item_type, item_id):
    """Deletes an item from the master inventory CSV by its ID."""
    all_items = _load_master_csv(item_type)
    # Rebuild the list, excluding the item with the matching ID
    items_to_keep = [item for item in all_items if item.get('id') != item_id]
    _save_master_csv(item_type, items_to_keep)

def get_master_item_map(item_type):
    """Returns a dictionary map of master items by their ID for quick lookups."""
    return {item['id']: item for item in _load_master_csv(item_type)}

# ======================================================================================
# CATEGORY & WORK ITEM MANAGEMENT (OPERATES ON JSON)
# ======================================================================================

def get_all_categories():
    return _load_json_data().get('categories', [])

def get_category_by_id(category_id):
    for category in get_all_categories():
        if category.get('id') == category_id:
            return category
    return None

def add_new_category(category_name):
    data = _load_json_data()
    new_category = {"id": str(uuid.uuid4()), "name": category_name, "work_items": []}
    data.setdefault('categories', []).append(new_category)
    _save_json_data(data)

def add_work_item_to_category(category_id, work_item):
    data = _load_json_data()
    for category in data.get('categories', []):
        if category.get('id') == category_id:
            category.setdefault('work_items', []).append(work_item)
            _save_json_data(data)
            break

def find_work_item_by_id(work_item_id):
    for category in get_all_categories():
        for item in category.get('work_items', []):
            if item.get('id') == work_item_id:
                return item
    return None

def update_work_item(category_id, updated_item):
    data = _load_json_data()
    for category in data.get('categories', []):
        if category.get('id') == category_id:
            category['work_items'] = [
                updated_item if item.get('id') == updated_item.get('id') else item
                for item in category.get('work_items', [])
            ]
            _save_json_data(data)
            break

def delete_work_item(category_id, work_item_id):
    data = _load_json_data()
    for category in data.get('categories', []):
        if category.get('id') == category_id:
            category['work_items'] = [
                item for item in category.get('work_items', []) if item.get('id') != work_item_id
            ]
            _save_json_data(data)
            break

# ======================================================================================
# PROJECT MANAGEMENT (OPERATES ON JSON)
# ======================================================================================

def get_projects():
    return _load_json_data().get('projects', [])

def get_project_by_id(project_id):
    for project in get_projects():
        if project.get('id') == project_id:
            return project
    return None

def save_new_project(project_name):
    data = _load_json_data()
    new_project_id = str(uuid.uuid4())
    new_project = {"id": new_project_id, "name": project_name, "items": []}
    data.setdefault('projects', []).append(new_project)
    _save_json_data(data)
    return new_project_id

def update_project(project_data):
    data = _load_json_data()
    data['projects'] = [
        project_data if p.get('id') == project_data.get('id') else p
        for p in data.get('projects', [])
    ]
    _save_json_data(data)
    