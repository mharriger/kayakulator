"""stations_loader.py
Loader for the INI-like stations format used in this repo.
Returns numpy arrays and dicts for keel, chines, gunwale, deckridge.
"""

import numpy as np
import re

def _parse_values_line(line):
    line = line.split(':', 1)[-1]
    parts = re.split(r'[,\s]+', line.strip())
    parts = [p for p in parts if p != '']
    return np.array([float(x) if x.lower() != 'nan' else np.nan for x in parts], dtype=float)


def load_stations_file(path):
    sections = {}
    current = None
    with open(path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('[') and line.endswith(']'):
                current = line[1:-1].strip().upper()
                sections[current] = []
                continue
            if current is None:
                continue
            sections[current].append(line)

    # parse stations
    meta = {}
    if 'STATIONS' not in sections:
        raise ValueError("Missing [STATIONS] section")
    st_lines = sections['STATIONS']
    stations = None
    m = re.search(r'count\s+(\d+)\s+spacing\s+([0-9.eE+-]+)', ' '.join(st_lines), flags=re.I)
    if m:
        n = int(m.group(1))
        s = float(m.group(2))
        stations = np.arange(n, dtype=float) * s
        meta['stations_count'] = n
        meta['spacing'] = s
    else:
        for l in st_lines:
            if ':' in l:
                _, rest = l.split(':', 1)
            else:
                rest = l
            vals = re.split(r'[,\s]+', rest.strip())
            vals = [v for v in vals if v != '']
            if vals:
                stations = np.array([float(x) for x in vals], dtype=float)
                break
    if stations is None:
        raise ValueError("Unable to parse station positions in [STATIONS]")
    n_st = stations.size

    # parse keel
    if 'KEEL' not in sections:
        raise ValueError("Missing [KEEL] section")
    keel_lines = sections['KEEL']
    keel_vals = None
    for l in keel_lines:
        if l.upper().startswith('HAB'):
            keel_vals = _parse_values_line(l)
            break
    if keel_vals is None:
        raise ValueError("No HAB line in [KEEL]")
    if keel_vals.size != n_st:
        raise ValueError(f"Keel HAB length {keel_vals.size} != stations {n_st}")

    # parse chines
    chines = []
    if 'CHINES' in sections:
        ch_lines = sections['CHINES']
        ch_text = '\n'.join(ch_lines)
        blocks = re.split(r'(?mi)^\s*chine\s+\d+', ch_text)
        blocks = [b for b in blocks[1:] if b.strip()]
        for b in blocks:
            hb = None
            hab = None
            for line in b.splitlines():
                if line.strip().upper().startswith('HB'):
                    hb = _parse_values_line(line)
                if line.strip().upper().startswith('HAB'):
                    hab = _parse_values_line(line)
            if hb is None or hab is None:
                raise ValueError("Each chine block must have HB and HAB lines")
            if hb.size != n_st or hab.size != n_st:
                raise ValueError("Chine lengths must match stations")
            chines.append({'hb': hb, 'hab': hab})

    # parse gunwale and deckridge
    def parse_pair_section(name):
        if name not in sections:
            raise ValueError(f"Missing [{name}] section")
        lines = sections[name]
        hb = None
        hab = None
        for l in lines:
            up = l.strip().upper()
            if up.startswith('HB'):
                hb = _parse_values_line(l)
            if up.startswith('HAB'):
                hab = _parse_values_line(l)
        if hb is None or hab is None:
            raise ValueError(f"[{name}] must contain HB and HAB lines")
        if hb.size != n_st or hab.size != n_st:
            raise ValueError(f"{name} lengths must match stations")
        return {'hb': hb, 'hab': hab}

    gunwale = parse_pair_section('GUNWALE')
    deckridge = parse_pair_section('DECKRIDGE')

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
        print('Usage: python stations_loader.py <file>')
        sys.exit(1)
    data = load_stations_file(sys.argv[1])
    print('Loaded stations:', data['stations'])
    print('Keel HAB:', data['keel_hab'])
    print('Chines count:', len(data['chines']))
