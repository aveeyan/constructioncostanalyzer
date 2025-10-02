# ======================================================================================
# app/routes.py - Version 3.2
# Status: Production Ready, Backward-Compatible
# ======================================================================================

from flask import Blueprint, render_template, redirect, url_for, request, flash
from . import data_manager
import collections
import uuid

main_bp = Blueprint('main_bp', __name__)

# --- UTILITY FUNCTIONS (No changes) ---

def parse_form_data(form):
    data = collections.defaultdict(list)
    items = collections.defaultdict(dict)
    for key, value in form.items():
        if '-' in key:
            parts = key.split('-')
            if len(parts) == 3:
                item_type, index, field = parts
                if value: items[f"{item_type}-{index}"][field] = value
    for key, value_dict in items.items():
        if 'id' in value_dict:
            item_type, _ = key.split('-')
            data[item_type].append(value_dict)
    return data

def standardize_item_key(items, key_name):
    for item in items:
        if key_name in item: item['Type'] = item.pop(key_name)
    return items

# --- CORE NAVIGATION & INVENTORY (No changes) ---

@main_bp.route('/')
def index():
    return redirect(url_for('main_bp.projects_list'))

# --- Find and REPLACE this entire function in app/routes.py ---

@main_bp.route('/inventory', methods=['GET', 'POST'])
def inventory_manager():
    if request.method == 'POST':
        item_type = request.form.get('item_type')
        if not item_type in ['labor', 'material', 'equipment']:
            flash('Invalid inventory category specified.', 'error')
            return redirect(url_for('main_bp.inventory_manager'))

        try:
            items_data = {}
            for key, value in request.form.items():
                if key.startswith('items['):
                    parts = key.strip(']').split('[')
                    _, item_id, field = parts
                    if item_id not in items_data:
                        items_data[item_id] = {'id': item_id}
                    items_data[item_id][field] = value
            
            for item_id, data in items_data.items():
                action = data.get('action')
                
                if action == 'delete':
                    data_manager.delete_master_item(item_type, item_id)
                
                elif action == 'update':
                    update_data = {"name": data.get('name'), "unit": data.get('unit'), "price": float(data.get('price', 0))}
                    if all(update_data.values()):
                        data_manager.update_master_item(item_type, item_id, update_data)

                elif action == 'create':
                    create_data = {"name": data.get('name'), "unit": data.get('unit'), "price": float(data.get('price', 0))}
                    if all(create_data.values()):
                        data_manager.add_master_item(item_type, create_data)

            flash(f'{item_type.capitalize()} inventory updated successfully.', 'success')

        except (ValueError, TypeError, KeyError) as e:
            flash(f'An error occurred while updating the inventory. Error: {e}', 'error')
        
        return redirect(url_for('main_bp.inventory_manager'))

    # ========================== THE CRITICAL FIX ==========================
    # GET Request Logic: The data_manager now provides a standardized 'name' key.
    # This logic must be updated to use that key and handle casing for the template.
    # The previous logic was looking for obsolete keys (e.g., 'LaborType').
    inventory_data = {}
    for item_type in ['labor', 'material', 'equipment']:
        raw_items = data_manager.get_master_data(item_type)
        
        standardized_items = []
        for item in raw_items:
            standardized_items.append({
                'id': item.get('id'),
                'name': item.get('name', 'N/A'),  # CORRECT: Use the 'name' key from the data manager.
                'unit': item.get('Unit'),        # Map 'Unit' to 'unit' for the template.
                'price': item.get('Price')       # Map 'Price' to 'price' for the template.
            })
        inventory_data[item_type] = standardized_items
    # ======================================================================

    return render_template('inventory_manager.html', 
        labor=inventory_data['labor'], 
        material=inventory_data['material'], 
        equipment=inventory_data['equipment'])

@main_bp.route('/categories', methods=['GET', 'POST'])
def categories_list():
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        if category_name:
            data_manager.add_new_category(category_name)
            flash(f"Category '{category_name}' created successfully.", 'success')
        else: flash('Category name cannot be empty.', 'error')
        return redirect(url_for('main_bp.categories_list'))
    categories = data_manager.get_all_categories()
    return render_template('categories_list.html', categories=categories)

@main_bp.route('/category/<category_id>', methods=['GET', 'POST'])
def category_detail(category_id):
    category = data_manager.get_category_by_id(category_id)
    if not category:
        flash('Category not found.', 'error')
        return redirect(url_for('main_bp.categories_list'))

    # ========================== THE CRITICAL FIX ==========================
    # DATA INTEGRITY LAYER: Ensure all work items, old and new, conform to the
    # latest data schema before being sent to the template.
    for item in category.get('work_items', []):
        # If 'basis_quantity' is missing, add it with a default of 1.
        if 'basis_quantity' not in item:
            item['basis_quantity'] = 1.0
        
        # If 'price_per_unit' is missing, calculate it on the fly.
        if 'price_per_unit' not in item:
            total = item.get('sum_total', 0)
            basis = item.get('basis_quantity', 1.0)
            # Ensure basis is not zero to prevent division errors
            item['price_per_unit'] = total / basis if basis > 0 else total
    # ======================================================================

    editing_item = None
    edit_item_id = request.args.get('edit_item_id')
    if edit_item_id:
        editing_item = data_manager.find_work_item_by_id(edit_item_id)

    form_state = { "name": "", "unit_of_measure": "Cubic Meter", "basis_quantity": 1.0, "labor": [], "material": [], "equipment": [] }
    if editing_item:
        form_state.update(editing_item)

    if request.method == 'POST':
        form_state['name'] = request.form.get('name', '')
        form_state['unit_of_measure'] = request.form.get('unit_of_measure', 'Cubic Meter')
        form_state['basis_quantity'] = request.form.get('basis_quantity', 1.0)
        parsed_data = parse_form_data(request.form)
        form_state.update(parsed_data)
        action = request.form.get('action')
        if action == 'add_labor': form_state['labor'].append({})
        elif action == 'add_material': form_state['material'].append({})
        elif action == 'add_equipment': form_state['equipment'].append({})

    master_labor = standardize_item_key(data_manager.get_master_data('labor'), 'LaborType')
    master_material = standardize_item_key(data_manager.get_master_data('material'), 'MaterialType')
    master_equipment = standardize_item_key(data_manager.get_master_data('equipment'), 'EquipmentType')

    return render_template('category_detail.html', 
        category=category, form_state=form_state, editing_item=editing_item,
        master_labor=master_labor, master_material=master_material, master_equipment=master_equipment)

def process_work_item_form(form, work_item_id=None):
    work_item_name = form.get('name')
    if not work_item_name: return None
    try:
        basis_quantity = float(form.get('basis_quantity', 1.0))
        if basis_quantity <= 0: basis_quantity = 1.0
    except (ValueError, TypeError): basis_quantity = 1.0
    total_cost = 0
    parsed_data = parse_form_data(form)
    processed_item = {
        "id": work_item_id or str(uuid.uuid4()), "name": work_item_name, 
        "unit_of_measure": form.get('unit_of_measure', 'Per Item'), "basis_quantity": basis_quantity,
        "labor": [], "material": [], "equipment": [],
        "labor_total": 0, "material_total": 0, "equipment_total": 0
    }
    for item_type in ['labor', 'material', 'equipment']:
        master_map = data_manager.get_master_item_map(item_type)
        group_subtotal = 0
        for item_data in parsed_data.get(item_type, []):
            try:
                master_item = master_map[int(item_data.get('id'))]
                quantity = float(item_data.get('quantity', 0))
                unit_price = float(master_item['Price'])
                subtotal = quantity * unit_price
                group_subtotal += subtotal
                processed_item[item_type].append({
                    'id': item_data.get('id'), 'name': master_item['Type'],
                    'quantity': quantity, 'unit_price': unit_price,
                    'subtotal': subtotal, 'unit': master_item['Unit']
                })
            except (ValueError, TypeError, KeyError): continue
        processed_item[f"{item_type}_total"] = group_subtotal
        total_cost += group_subtotal
    processed_item['total_cost_per_unit'] = total_cost
    processed_item['contractor_overhead_15_percent'] = total_cost * 0.15
    processed_item['sum_total'] = total_cost * 1.15
    processed_item['price_per_unit'] = processed_item['sum_total'] / basis_quantity
    return processed_item

@main_bp.route('/category/<category_id>/save_item', methods=['POST'])
def save_work_item(category_id):
    final_item = process_work_item_form(request.form)
    if not final_item:
        flash('Work Item Name is required.', 'error')
        return redirect(url_for('main_bp.category_detail', category_id=category_id))
    data_manager.add_work_item_to_category(category_id, final_item)
    flash(f"Work Item '{final_item['name']}' saved successfully.", 'success')
    return redirect(url_for('main_bp.category_detail', category_id=category_id))

@main_bp.route('/category/<category_id>/update_item/<work_item_id>', methods=['POST'])
def update_work_item(category_id, work_item_id):
    updated_item = process_work_item_form(request.form, work_item_id=work_item_id)
    if not updated_item:
        flash('Work Item Name is required.', 'error')
        return redirect(url_for('main_bp.category_detail', category_id=category_id, edit_item_id=work_item_id))
    data_manager.update_work_item(category_id, updated_item)
    flash(f"Work Item '{updated_item['name']}' updated successfully.", 'success')
    return redirect(url_for('main_bp.category_detail', category_id=category_id))

@main_bp.route('/category/<category_id>/delete_item/<work_item_id>', methods=['POST'])
def delete_work_item(category_id, work_item_id):
    data_manager.delete_work_item(category_id, work_item_id)
    flash('Work Item deleted successfully.', 'success')
    return redirect(url_for('main_bp.category_detail', category_id=category_id))

# --- Find and REPLACE this entire function in app/routes.py ---

@main_bp.route('/projects', methods=['GET', 'POST'])
def projects_list():
    if request.method == 'POST':
        project_name = request.form.get('project_name')
        if project_name:
            new_project_id = data_manager.save_new_project(project_name)
            flash(f"Project '{project_name}' created.", 'success')
            return redirect(url_for('main_bp.project_detail', project_id=new_project_id))
        else:
            flash('Project name cannot be empty.', 'error')
    
    # ========================== THE CRITICAL FIX ==========================
    # We must process the projects to calculate the grand_total for the list view.
    # This was the source of the latent bug.
    all_projects = data_manager.get_projects()
    for project in all_projects:
        grand_total = 0
        # Ensure 'items' key exists and is a list
        for item in project.get('items', []):
            # Ensure quantity and unit_price exist and are numbers
            quantity = item.get('quantity', 0)
            unit_price = item.get('unit_price', 0)
            grand_total += quantity * unit_price
        project['grand_total'] = grand_total
    # ======================================================================

    return render_template('projects_list.html', projects=all_projects)
# --- Find and REPLACE this entire function in app/routes.py ---

@main_bp.route('/project/<project_id>', methods=['GET', 'POST'])
def project_detail(project_id):
    project = data_manager.get_project_by_id(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('main_bp.projects_list'))

    if request.method == 'POST':
        for item in project.get('items', []):
            new_quantity = request.form.get(f'quantity-{item["instance_id"]}')
            if new_quantity is not None:
                try:
                    item['quantity'] = float(new_quantity)
                except (ValueError, TypeError):
                    item['quantity'] = 0
        data_manager.update_project(project)
        flash('Project updated successfully.', 'success')
        return redirect(url_for('main_bp.project_detail', project_id=project_id))

    # ========================== THE CRITICAL FIX ==========================
    # DATA INTEGRITY LAYER: We must calculate the 'total' for each item and
    # the 'grand_total' for the project before rendering. This was the source
    # of the UndefinedError. This calculation must happen on every GET request
    # to ensure the display is always accurate.
    grand_total = 0
    for item in project.get('items', []):
        quantity = item.get('quantity', 0)
        unit_price = item.get('unit_price', 0)
        item_total = quantity * unit_price
        item['total'] = item_total  # This injects the required 'total' key.
        grand_total += item_total
    project['grand_total'] = grand_total
    # ======================================================================

    return render_template('project_detail.html', project=project, all_work_items=data_manager.get_all_categories())

@main_bp.route('/project/<project_id>/add_item', methods=['POST'])
def add_item_to_project(project_id):
    project = data_manager.get_project_by_id(project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('main_bp.projects_list'))
    work_item_id = request.form.get('work_item_id')
    quantity = request.form.get('quantity', '1.0')
    work_item = data_manager.find_work_item_by_id(work_item_id)
    if not work_item:
        flash('Work item not found.', 'error')
        return redirect(url_for('main_bp.project_detail', project_id=project_id))
    new_item = {
        "instance_id": str(uuid.uuid4()), "work_item_id": work_item_id,
        "name": work_item.get('name'), "unit_of_measure": work_item.get('unit_of_measure'),
        "unit_price": work_item.get('sum_total', 0), "quantity": float(quantity)
    }
    project.setdefault('items', []).append(new_item)
    data_manager.update_project(project)
    flash(f"Added '{new_item['name']}' to the project.", 'success')
    return redirect(url_for('main_bp.project_detail', project_id=project_id))
