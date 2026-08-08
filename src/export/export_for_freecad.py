#Simple function for export to a FreeCAD-friendly STEP file.

from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.BRep import BRep_Builder
from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCC.Core.Interface import Interface_Static
from OCC.Core.IFSelect import IFSelect_RetDone

def export_for_freecad(shapes_list, filename="freecad_ready.stp"):
    # 1. Create an empty compound container
    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    
    # 2. Pack all your shapes into the single compound
    for shape in shapes_list:
        builder.Add(compound, shape)
        
    # 3. Export the single compound
    step_writer = STEPControl_Writer()
    Interface_Static.SetCVal("write.step.schema", "AP214")
    step_writer.Transfer(compound, STEPControl_AsIs)
    
    if step_writer.Write(filename) == IFSelect_RetDone:
        print(f"Exported {len(shapes_list)} shapes inside a Compound to {filename}")
