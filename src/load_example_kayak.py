from kayakulator_document import KayakulatorDocument
from offsets.json_offset_loader import load_offset_file, get_metadata

doc = KayakulatorDocument('example')

offsets = load_offset_file('../data/SeaTour15EXP.offsets.json')
doc = KayakulatorDocument()
doc.offsets = offsets
print(doc.offsets.format_table())
doc.model_kayak()