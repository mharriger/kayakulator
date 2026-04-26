"""offset_loader.py
Loader for the JSON offset table format defined in offset_schema.json.
Returns numpy arrays and dicts for keel, chines, gunwale, deckridge.
Output format matches stations_loader.py for compatibility.
"""

import json
import numpy as np
import jsonschema
import os


def _get_schema_path():
    """Get the path to the offset schema JSON file."""
    # Schema is in parse_offset_table_skill/references/offset_schema.json
    # relative to the parent of kayakulator2
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    schema_path = os.path.join(base_dir, 'parse_offset_table_skill', 'references', 'offset_schema.json')
    return schema_path


def load_offset_file(path):
    """Load a JSON offset table and return data in the same format as stations_loader.
    
    Args:
        path: Path to the JSON offset table file
        
    Returns:
        dict with keys:
            - stations: numpy array of station locations
            - keel_hab: numpy array of keel heights
            - chines: list of dicts with 'hb' and 'hab' numpy arrays
            - gunwale: dict with 'hb' and 'hab' numpy arrays
            - deckridge: dict with 'hb' and 'hab' numpy arrays
            - meta: dict with metadata (units, name)
            
    Raises:
        jsonschema.ValidationError: If the file does not match the schema
        FileNotFoundError: If the file or schema cannot be found
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load and validate against schema
    schema_path = _get_schema_path()
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)
    
    jsonschema.validate(data, schema)
    
    stations_data = data['stations']
    n_st = len(stations_data)
    
    # Extract station locations
    stations = np.array([s['location'] for s in stations_data], dtype=float)
    
    # Extract keel heights (single value per station)
    keel_vals = np.array([s['keel'] for s in stations_data], dtype=float)
    
    # Extract gunwale (hab, hb pairs)
    gunwale_hab = np.array([s['gunwale']['hab'] for s in stations_data], dtype=float)
    gunwale_hb = np.array([s['gunwale']['hb'] for s in stations_data], dtype=float)
    gunwale = {'hab': gunwale_hab, 'hb': gunwale_hb}
    
    # Extract chines (each station can have multiple chines)
    # Determine the number of chines from the first station
    n_chines = len(stations_data[0]['chines'])
    
    # Build chines list
    chines = []
    for ch_idx in range(n_chines):
        ch_hab = np.array([s['chines'][ch_idx]['hab'] for s in stations_data], dtype=float)
        ch_hb = np.array([s['chines'][ch_idx]['hb'] for s in stations_data], dtype=float)
        chines.append({'hab': ch_hab, 'hb': ch_hb})
    
    # Extract deckridge (hab, hb pairs)
    deckridge_hab = np.array([s['deckridge']['hab'] for s in stations_data], dtype=float)
    deckridge_hb = np.array([s['deckridge']['hb'] for s in stations_data], dtype=float)
    deckridge = {'hab': deckridge_hab, 'hb': deckridge_hb}
    
    # Build metadata
    meta = {}
    if 'units' in data:
        meta['units'] = data['units']
    if 'name' in data:
        meta['name'] = data['name']
    meta['stations_count'] = n_st
    
    return {
        'stations': stations,
        'keel_hab': keel_vals,
        'chines': chines,
        'gunwale': gunwale,
        'deckridge': deckridge,
        'meta': meta
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python offset_loader.py <file>')
        sys.exit(1)
    data = load_offset_file(sys.argv[1])
    print('Loaded stations:', data['stations'])
    print('Keel HAB:', data['keel_hab'])
    print('Chines count:', len(data['chines']))
    print('Gunwale:', data['gunwale'])
    print('Deckridge:', data['deckridge'])
    print('Meta:', data['meta'])
