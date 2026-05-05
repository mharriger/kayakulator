"""json_offset_loader.py
Loader for the JSON offset table format defined in offset_schema.json.
Output is an OffsetTable object
"""

import json
import jsonschema
import os

from .offset_table import OffsetTable
from .member import KEEL, DECKRIDGE, GUNWALE, chine

def _get_schema_path():
    """Get the path to the offset schema JSON file."""
    # Schema is in parse_offset_table_skill/references/offset_schema.json
    # relative to the parent of kayakulator2
    base_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(base_dir, 'offset_schema.json')
    return schema_path

def _get_conversion_factor(units):
    """Get the conversion factor from the given units to mm.
    
    Args:
        units: Unit string ('mm', 'cm', 'inches', 'feet')
        
    Returns:
        Conversion factor (multiply the measurement by this to get mm)
    """
    conversion_factors = {
        'mm': 1.0,
        'cm': 10.0,
        'inches': 25.4,
        'feet': 304.8
    }
    return conversion_factors.get(units, 1.0)

def _get_data_and_validate(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load and validate against schema
    schema_path = _get_schema_path()
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    jsonschema.validate(data, schema)
    return data

def load_offset_file(path):
    """Load a JSON offset table and return an OffsetTable object
    
    Args:
        path: Path to the JSON offset table file
        
    Returns:
        OffsetTable object with all measurements converted to mm
            
    Raises:
        jsonschema.ValidationError: If the file does not match the schema
        FileNotFoundError: If the file or schema cannot be found
    """
    data = _get_data_and_validate(path)
    
    # Get conversion factor based on units
    units = data.get('units', 'mm')
    conversion_factor = _get_conversion_factor(units)
    
    table = OffsetTable()
    table.station_locations = {idx: s['location'] * conversion_factor for idx, s in enumerate(data['stations'])}

    for idx, station in enumerate(data['stations']):
        table.set_offset(idx, KEEL, x=0, z=station['keel'] * conversion_factor)
        table.set_offset(idx, DECKRIDGE, 
                        x=station['deckridge']['hb'] * conversion_factor, 
                        z=station['deckridge']['hab'] * conversion_factor)
        table.set_offset(idx, GUNWALE, 
                        x=station['gunwale']['hb'] * conversion_factor, 
                        z=station['gunwale']['hab'] * conversion_factor)
        for chine_idx, chine_data in enumerate(station['chines']):
            table.set_offset(idx, chine(chine_idx), 
                            x=chine_data['hb'] * conversion_factor, 
                            z=chine_data['hab'] * conversion_factor)

    return table

def get_metadata(path):
    """
    Return the name and units of the kayak from the file
    """
    data = _get_data_and_validate(path)
    return {key: data[key] for key in ['name', 'units']}

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python offset_loader.py <file>')
        sys.exit(1)
    data = load_offset_file(sys.argv[1])
    print(data.format_table())
