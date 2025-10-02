def format_unit(value: str) -> str:
    """
    Formats a unit string for display.
    Turns 'PerKg' into '1 kg', 'PerDay' into '1 Day', etc.
    This is also where future, more complex rules can live.
    """
    if not isinstance(value, str):
        return value

    # Future-proofing: Define specific overrides here
    # For example, to implement the "Shift = 8 hrs" rule:
    # if value.lower() == 'pershift':
    #     return '8 hrs'

    # General rule for 'Per' prefix
    if value.lower().startswith('per'):
        # Strip 'Per' and format: 'PerKg' -> 'Kg', 'PerDay' -> 'Day'
        unit_name = value[3:]
        # Simple attempt to make it lowercase if it's not something like 'CubicM'
        if unit_name.isupper() or len(unit_name) <= 2:
             unit_name = unit_name.lower()
        return f"1 {unit_name}"
    
    # Fallback for units without 'Per' prefix like 'CubicM'
    return f"1 {value}"
