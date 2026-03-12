import os
import json
import FreeCAD as App
import Part, Draft

# Hard-wired JSON filename - change to match your installation
json_path = r"D:\GitHub\PICO-wordsearch-clock\firmware-PICO\clockface.json"

if App.ActiveDocument==None:
    doc = App.newDocument("PrintedWordsearch")
    firstRun=True
else:
    doc = App.ActiveDocument
    firstRun=False

# Delete all existing objects in the document
for obj in doc.Objects:
    doc.removeObject(obj.Name)

# ---------- Helper: pick a usable bold font ----------
def find_font(explicit_path=None):
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path
    candidates = [
        # Windows
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\verdana.ttf",
        r"C:\Windows\Fonts\seguisb.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        # Flatpak
        "/usr/share/fonts/liberation-fonts/LiberationSans-Bold.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Bold TTF not found. Set font_path explicitly.")

# ---------- Helper: centre a ShapeString in the cell ----------
def center_shapestring(shape_obj, cell_size, z_top_of_base):
    App.ActiveDocument.recompute()
    bbox = shape_obj.Shape.BoundBox
    text_w, text_h = bbox.XLength, bbox.YLength
    x_offset = (cell_size - text_w) / 2.0 - bbox.XMin
    y_offset = (cell_size - text_h) / 2.0 - bbox.YMin
    shape_obj.Placement.Base = App.Vector(x_offset, y_offset, z_top_of_base)
    App.ActiveDocument.recompute()

# ---------- Helper: group wires into outers with their inner-hole wires ----------
def group_outer_inner_wires(wires):
    """
    Return a list of tuples: [(outer_wire, [inner_wires]), ...]
    We classify by area (biggest first) and confirm containment using isInside().
    """
    # Filter closed wires
    cwires = [w for w in wires if w.isClosed()]
    if not cwires:
        raise RuntimeError("No closed wires found in the ShapeString (font issue?).")

    # Sort by absolute area descending (outer loops tend to be largest)
    cwires.sort(key=lambda w: abs(Part.Face(w).Area), reverse=True)

    groups = []
    used = set()

    for i, outer in enumerate(cwires):
        if i in used:
            continue
        outer_face = Part.Face(outer)
        inners = []
        for j, inner in enumerate(cwires):
            if j == i or j in used:
                continue
            # Take a sample point from the inner (a vertex) and test if inside the outer face
            try:
                p = inner.Vertexes[0].Point
            except Exception:
                continue
            if outer_face.isInside(p, 1e-6, True):
                inners.append(inner)
                used.add(j)
        groups.append((outer, inners))
        used.add(i)
    return groups

# ---------- Helper: build a solid from text (preserving holes via CUTs) ----------
def shapestring_to_extruded_solid_by_cut(shape_obj, height):
    """
    Convert ShapeString to a solid:
      - For each outer wire, extrude a solid.
      - For each of its inner wires (holes), extrude and CUT it from the outer.
      - Fuse solids from multiple glyph islands into one.
    """
    groups = group_outer_inner_wires(shape_obj.Shape.Wires)
    solids = []

    for outer, inners in groups:
        outer_face = Part.Face(outer)
        outer_solid = outer_face.extrude(App.Vector(0, 0, height))

        # Cut each inner (hole)
        for inner in inners:
            inner_face = Part.Face(inner)
            inner_solid = inner_face.extrude(App.Vector(0, 0, height))
            try:
                outer_solid = outer_solid.cut(inner_solid)
            except Exception:
                # If cut fails (rare), skip that inner to avoid aborting
                pass

        solids.append(outer_solid)

    # Fuse all separate solids into a single one
    solid = solids[0]
    for s in solids[1:]:
        try:
            solid = solid.fuse(s)
        except Exception:
            solid = Part.makeCompound([solid, s])
    return solid

# ---------- Core builder: one tile at origin ----------
def build_letter_tile(letter="A",
                      cell_size=10.0,
                      base_thick=1.0,
                      font_size=6.5,
                      letter_thickness_mm=0.8,
                      font_path=None,
                      engrave=False,
                      empty_tile=False,
                      behind_letter_panel_thickness=0):
    """
    Returns a Part.Shape of the completed tile located at the origin.
    - If engrave=False: raised letter fused on top of the App.
    - If engrave=True: letter cut into the base (same extrusion height).
    """
    # Base
    base = Part.makeBox(cell_size, cell_size, base_thick)

    if empty_tile:
        return base

    # Text
    font = find_font(font_path)
    shape = Draft.makeShapeString(String=letter, FontFile=font, Size=font_size, Tracking=0)
    App.ActiveDocument.recompute()

    # Centre text and sit it on top of the base (z = base_thick)
    center_shapestring(shape, cell_size, base_thick)

    # Create the letter solid (extrude upward)
    letter_solid = shapestring_to_extruded_solid_by_cut(shape, abs(letter_thickness_mm))
    try:
        App.ActiveDocument.removeObject(shape.Name)
    except Exception:
        pass

    # Combine with base
    if engrave:
        plane_point = App.Vector(cell_size / 2.0, 0, 0)
        plane_normal = App.Vector(1, 0, 0)
        letter_solid = letter_solid.mirror(plane_point, plane_normal)        
        letter_solid.translate(App.Vector(0,0,-letter_thickness_mm))
        tile = base.cut(letter_solid)
        if behind_letter_panel_thickness>0:
            behindPanel = Part.makeBox(cell_size, cell_size, behind_letter_panel_thickness)
            behindPanel.translate(App.Vector(0,0,letter_thickness_mm))
            letter_solid=letter_solid.fuse(behindPanel)
    else:
        tile = App.fuse(letter_solid)
    return (tile, letter_solid)

# ---------- Main: generate both raised and engraved tiles ----------
def make_grid(grid=("ABC","123","XYZ"),
              letter_cell_size_mm=10.0,
              letter_cell_base_thickness_mm=2.0,
              font_size=6.5,
              letter_thickness_mm=1.6,
              font_path=None,
              doc_name="LetterGrid",
              outer_frame_size_mm=3.0,
              holder_border_gap_mm= 0.25,
              separator_size_mm=1.5,
              separator_thickness_mm=3.0,
              letter_grid_border_mm=0.5,
              led_panel_thickness_mm = 0.7,
              led_holder_border_mm=5,
              inner_holder_back_thickness_mm=7,
              outer_holder_back_thickness_mm=10,
              led_holder_inner_back_thickness_mm=3,
              snap_fit_radius_mm = 0.5,
              snap_fit_gap_mm =0.05,
              snap_fit_slot_margin_mm = 15.0,
              snap_fit_slot_extend_mm = 3.0,
              engrave_letters=False,
              no_letters_on_tiles=False,
              behind_letter_panel_thickness=0,
              speaker=False):
                  
    if speaker:
        inner_holder_back_thickness_mm=inner_holder_back_thickness_mm+20
        

    grid_width_letters = len(grid[0])
    grid_depth_letters = len(grid)

    grid_width_mm = letter_cell_size_mm * grid_width_letters
    grid_depth_mm = letter_cell_size_mm * grid_depth_letters

    total_width_mm = grid_width_mm+(2*outer_frame_size_mm)+(2*letter_grid_border_mm)
    total_depth_mm = grid_depth_mm+(2*outer_frame_size_mm)+(2*letter_grid_border_mm)

    surround_thick=letter_cell_base_thickness_mm+separator_thickness_mm+outer_holder_back_thickness_mm+led_panel_thickness_mm+behind_letter_panel_thickness

#  Make the grid of letters: letter_grid

    if no_letters_on_tiles:
        # for speedy debugging we just make the grid as a box
        letter_grid=Part.makeBox(grid_width_mm,grid_depth_mm,letter_cell_base_thickness_mm)
        solid_grid=Part.makeBox(grid_width_mm,grid_depth_mm,letter_cell_base_thickness_mm)
    else:
        # build each tile from the grid of letters
        letter_grid = None
        solid_grid = None
        y=len(grid)-1
        for row in grid:
            x=len(row)-1
            for ch in row:
                tile, letter_solid = build_letter_tile(ch, letter_cell_size_mm, letter_cell_base_thickness_mm, font_size, letter_thickness_mm, font_path, engrave=engrave_letters,empty_tile=no_letters_on_tiles,behind_letter_panel_thickness=behind_letter_panel_thickness)
                tile.translate(App.Vector(x*letter_cell_size_mm,y*letter_cell_size_mm,0))
                if letter_grid == None:
                    letter_grid = tile
                else:
                    letter_grid = letter_grid.fuse(tile)

                letter_solid.translate(App.Vector(x*letter_cell_size_mm,y*letter_cell_size_mm,0))
                if solid_grid == None:
                    solid_grid = letter_solid
                else:
                    solid_grid = solid_grid.fuse(letter_solid)

                x=x-1
            y=y-1


# Make the outer panel

    panel=Part.makeBox(total_width_mm,total_depth_mm,surround_thick)

    # Cut a hole for the letters

    panel_letter_cut=Part.makeBox(grid_width_mm+(2*letter_grid_border_mm),grid_depth_mm+(2*letter_grid_border_mm),surround_thick,
            App.Vector(outer_frame_size_mm,outer_frame_size_mm,letter_cell_base_thickness_mm))

    panel= panel.cut(panel_letter_cut)

    # Make a hole for the letters

    letter_hole=Part.makeBox(grid_width_mm,grid_depth_mm,letter_cell_base_thickness_mm,
            App.Vector(outer_frame_size_mm+letter_grid_border_mm,outer_frame_size_mm+letter_grid_border_mm,0))

    panel = panel.cut(letter_hole)
    
    # Add the letter grid to the panel

    letter_grid.translate(App.Vector(outer_frame_size_mm+letter_grid_border_mm,outer_frame_size_mm+letter_grid_border_mm,0))
    solid_grid.translate(App.Vector(outer_frame_size_mm+letter_grid_border_mm,outer_frame_size_mm+letter_grid_border_mm,0))

    panel=panel.fuse(letter_grid)

# Make a separator grid to isolate each led behind the front panel

    separater_outer=Part.makeBox(grid_width_mm,grid_depth_mm,separator_thickness_mm, 
        App.Vector(outer_frame_size_mm+letter_grid_border_mm,outer_frame_size_mm+letter_grid_border_mm,0))

    separater_inner=Part.makeBox(grid_width_mm-separator_size_mm,grid_depth_mm-separator_size_mm,separator_thickness_mm, 
        App.Vector(outer_frame_size_mm+letter_grid_border_mm+separator_size_mm/2,
            outer_frame_size_mm+letter_grid_border_mm+separator_size_mm/2,0))

    separator = separater_outer.cut(separater_inner)

    for sep_x_num in range(1,grid_width_letters):
        sep_x = (sep_x_num*letter_cell_size_mm)+outer_frame_size_mm+letter_grid_border_mm-(separator_size_mm/2)
        sep_pos = App.Vector(sep_x,outer_frame_size_mm+letter_grid_border_mm,0)
        sep = Part.makeBox(separator_size_mm,grid_depth_mm,separator_thickness_mm,sep_pos)
        separator = separator.fuse(sep)

    for sep_y_num in range(1,grid_depth_letters):
        sep_y = (sep_y_num*letter_cell_size_mm)+outer_frame_size_mm+letter_grid_border_mm-(separator_size_mm/2)
        sep_pos = App.Vector(outer_frame_size_mm+letter_grid_border_mm,sep_y,0)
        sep = Part.makeBox(grid_width_mm,separator_size_mm,separator_thickness_mm,sep_pos)
        separator = separator.fuse(sep)

# Make a panel that stands in for the led array and place it behind the separator
# Place it behind the separator

    leds=Part.makeBox(grid_width_mm,grid_depth_mm,led_panel_thickness_mm, 
        App.Vector(
            outer_frame_size_mm+letter_grid_border_mm,
            outer_frame_size_mm+letter_grid_border_mm,
            letter_cell_base_thickness_mm+separator_thickness_mm))
            
# Make the holder for the led panel - should project into the front panel

    inner_holder_back_width_mm = total_width_mm-((2*holder_border_gap_mm)+(2*outer_frame_size_mm))
    inner_holder_back_depth_mm = total_depth_mm-((2*holder_border_gap_mm)+(2*outer_frame_size_mm))
    
    inner_border_x = outer_frame_size_mm+holder_border_gap_mm
    inner_border_y = outer_frame_size_mm+holder_border_gap_mm

    holder=Part.makeBox(inner_holder_back_width_mm,
            inner_holder_back_depth_mm,
            inner_holder_back_thickness_mm+outer_holder_back_thickness_mm,
          App.Vector(inner_border_x,inner_border_y,0))

    holder_border=Part.makeBox(total_width_mm,total_depth_mm,inner_holder_back_thickness_mm,
          App.Vector(0,0,outer_holder_back_thickness_mm))

    holder=holder.fuse(holder_border)

    holder_cut=Part.makeBox(inner_holder_back_width_mm-led_holder_border_mm*2,
            inner_holder_back_depth_mm-led_holder_border_mm*2,
            inner_holder_back_thickness_mm+outer_holder_back_thickness_mm,
          App.Vector(outer_frame_size_mm+holder_border_gap_mm+led_holder_border_mm,
            outer_frame_size_mm+holder_border_gap_mm+led_holder_border_mm,
            -led_holder_inner_back_thickness_mm))

    holder = holder.cut(holder_cut)
    
    # Now add some pillars to hold a PICO
    
    boardDepth = 52.0
    boardWidth = 21.0
    boardThickness = 5.0
    holeRadius = 2.0
    holeYSpacing = 47.0
    holeXSpacing = 11.4
    
    pico = Part.makeBox(boardWidth,boardDepth,boardThickness)
    holeX=(boardWidth-holeXSpacing)/2.0
    holeY=(boardDepth-holeYSpacing)/2.0
    hole = Part.makeCylinder(holeRadius,boardThickness,
        App.Vector(holeX,holeY,0))
    
    pico=pico.cut(hole)
    hole.translate(App.Vector(holeXSpacing,0,0))
    pico=pico.cut(hole)
    hole.translate(App.Vector(0,holeYSpacing,0))
    pico=pico.cut(hole)
    hole.translate(App.Vector(-holeXSpacing,0,0))
    pico=pico.cut(hole)

    pillarRadius=2.0
    pillarHeight=6
    holeRadius=0.9
    
    if speaker:
        pico_offset = -40
        hole_offset = 20
    else:
        pico_offset = 40
        hole_offset = 0

    pico_x =(total_width_mm-boardWidth)/2
    pico_y =(total_depth_mm-boardDepth)/2+pico_offset
    pico_z = inner_holder_back_thickness_mm+outer_holder_back_thickness_mm-led_holder_inner_back_thickness_mm-pillarHeight
    pico.translate(App.Vector(pico_x,pico_y,0))
    
    def makePillar(v):
        pillar=Part.makeCylinder(pillarRadius,pillarHeight)
        pillar_hole=Part.makeCylinder(holeRadius,pillarHeight)
        pillar=pillar.cut(pillar_hole)
        pillar.translate(v)
        return pillar

        
    pico_x =(total_width_mm-holeXSpacing)/2
    pico_y =(total_depth_mm-holeYSpacing)/2 + pico_offset
    
    p = makePillar(App.Vector(pico_x, pico_y, pico_z))
    holder=holder = holder.fuse(p)
    p.translate(App.Vector(holeXSpacing,0,0))
    holder=holder.fuse(p)
    p.translate(App.Vector(0,holeYSpacing,0)) 
    holder=holder.fuse(p)
    p.translate(App.Vector(-holeXSpacing,0,0))
    holder=holder.fuse(p)
    
    cable_hole_radius = 7.0
    hole_x = total_width_mm/2.0
    hole_y = total_depth_mm/2.0+hole_offset
    hole_z = inner_holder_back_thickness_mm+outer_holder_back_thickness_mm-led_holder_inner_back_thickness_mm
    cable_hole = Part.makeCylinder(cable_hole_radius, led_holder_inner_back_thickness_mm,App.Vector(hole_x, hole_y, hole_z))
    holder = holder.cut(cable_hole)

# Now add a speaker
    if speaker:
        sp_boardDepth = 42.0
        sp_boardWidth = 42.0
        sp_holeXSpacing = 32.5
        sp_holeYSpacing = 32.5
        sp_holeXInset = 4.75
        sp_holeYInset = 4.75
        sp_holeDiam = 2.5
        sp_y_offset=50
        sp_unit_outer_hole_radius=39.0/2.0
        sp_unit_retainer_thickness=1.0
        sp_unit_retainer_height=3.0
        pillarHeight=3
        
        sp_x = (total_width_mm-sp_boardWidth)/2.0+sp_holeXInset
        sp_y = (total_depth_mm-sp_boardDepth)/2.0+sp_holeYInset+sp_y_offset
        sp_z = inner_holder_back_thickness_mm+outer_holder_back_thickness_mm-led_holder_inner_back_thickness_mm-pillarHeight
        
        p = makePillar(App.Vector(sp_x, sp_y, sp_z))
        holder=holder.fuse(p)
        p.translate(App.Vector(sp_holeXSpacing,0,0))
        holder=holder.fuse(p)
        p.translate(App.Vector(0,sp_holeYSpacing,0))
        holder=holder.fuse(p)
        p.translate(App.Vector(-sp_holeXSpacing,0,0))
        holder=holder.fuse(p)

        centreX = total_width_mm/2.0
        centreY = total_depth_mm/2.0+sp_y_offset
        centrePos = App.Vector(centreX,centreY,0)
        bottomX = centreX-(sp_boardWidth/2.0)
        baseDepth=led_holder_inner_back_thickness_mm
        
        sp_retainer_outer=Part.makeCylinder(sp_unit_outer_hole_radius+sp_unit_retainer_thickness,sp_unit_retainer_height,
            App.Vector(centreX,centreY,hole_z-sp_unit_retainer_height))
        sp_retainer_inner=Part.makeCylinder(sp_unit_outer_hole_radius,sp_unit_retainer_height,
            App.Vector(centreX,centreY,hole_z-sp_unit_retainer_height))
            
        sp_retainer=sp_retainer_outer.cut(sp_retainer_inner)
        
        holder=holder.fuse(sp_retainer)

        startPos = App.Vector(bottomX+(sp_holeDiam/2.0)+2, centreY,hole_z)

        holeCut=Part.makeCylinder((sp_holeDiam) / 2.0,baseDepth,App.Vector(0,0,0))

        holeCut.translate(startPos)
        
        holes=24

        for pipePos in range(0,holes):
            rotation=((pipePos/holes))* 360
            holeCut.rotate(centrePos,App.Vector(0,0,1),rotation)
            holder = holder.cut(holeCut)
            holeCut.rotate(centrePos,App.Vector(0,0,1),-rotation)

        startPos = App.Vector(bottomX+(sp_holeDiam/2.0)+6, centreY,hole_z)

        holeCut=Part.makeCylinder((sp_holeDiam) / 2.0,baseDepth,App.Vector(0,0,0))

        holeCut.translate(startPos)
        
        holes=15

        for pipePos in range(0,holes):
            rotation=((pipePos/holes))* 360
            holeCut.rotate(centrePos,App.Vector(0,0,1),rotation)
            holder = holder.cut(holeCut)
            holeCut.rotate(centrePos,App.Vector(0,0,1),-rotation)

        holes=9
        
        startPos = App.Vector(bottomX+(sp_holeDiam/2.0)+10, centreY,hole_z)

        holeCut=Part.makeCylinder((sp_holeDiam) / 2.0,baseDepth,App.Vector(0,0,0))

        holeCut.translate(startPos)

        for pipePos in range(0,holes):
            rotation=((pipePos/holes))* 360
            holeCut.rotate(centrePos,App.Vector(0,0,1),rotation)
            holder = holder.cut(holeCut)
            holeCut.rotate(centrePos,App.Vector(0,0,1),-rotation)

        startPos = App.Vector(bottomX+(sp_holeDiam/2.0)+14, centreY,hole_z)

        holeCut=Part.makeCylinder((sp_holeDiam) / 2.0,baseDepth,App.Vector(0,0,0))

        holeCut.translate(startPos)
        
        holes=7

        for pipePos in range(0,holes):
            rotation=((pipePos/holes))* 360
            holeCut.rotate(centrePos,App.Vector(0,0,1),rotation)
            holder = holder.cut(holeCut)
            holeCut.rotate(centrePos,App.Vector(0,0,1),-rotation)
            
        # now add a place to put the mp3 player
        
        mp3_width=24.5
        mp3_depth=22.0
        wall_thickness=2.0
        wall_height=15.0
        
        mp3_outer_box = Part.makeBox(mp3_width+(wall_thickness*2),mp3_depth+(wall_thickness*2),wall_height)
        mp3_inner_box = Part.makeBox(mp3_width,mp3_depth,wall_height,App.Vector(wall_thickness,wall_thickness,0))
        mp3_box = mp3_outer_box.cut(mp3_inner_box)
        mp3_box.translate(App.Vector(10,40,hole_z-wall_height))
        holder = holder.fuse(mp3_box)      
        
        button_hole_radius = 13.0/2.0
        button_separation = 25.0
        button_y_margin = 20.0
        button_extra_gap=10
        button_space = (total_width_mm-sp_boardWidth)/2.0
        button_margin=(button_space-button_separation)/2.0
        button_x = centreX-(button_margin+button_extra_gap)
        button_hole_pos=App.Vector(button_x,button_y_margin,hole_z)
        button_hole = Part.makeCylinder(button_hole_radius,baseDepth,button_hole_pos)
        holder=holder.cut(button_hole)
        button_hole.translate(App.Vector(-button_separation,0,0))
        holder=holder.cut(button_hole)
        button_hole.translate(App.Vector(button_separation+2*button_margin+2*button_extra_gap,0,0))
        holder=holder.cut(button_hole)
        button_hole.translate(App.Vector(button_separation,0,0))
        holder=holder.cut(button_hole)
        
        
        tilt_radius=4.0/2
        tilt_length=15.0
        tilt_holder_thickness=1.5
        slot_width=2.0
        tilt_outer_box = Part.makeCylinder(tilt_radius+tilt_holder_thickness,tilt_length)
        tilt_inner_box = Part.makeCylinder(tilt_radius,tilt_length)
        tilt_box=tilt_outer_box.cut(tilt_inner_box)
        slot=Part.makeBox(slot_width,tilt_radius+tilt_holder_thickness,tilt_length,
            App.Vector(-slot_width/2.0,-(tilt_radius+tilt_holder_thickness),0))
        tilt_box=tilt_box.cut(slot)
        tilt_box.translate(App.Vector(120,80,hole_z-tilt_length))
        holder=holder.fuse(tilt_box)

    
# Now create the snap-fit cylinders and cut the fitting pieces

    # Create the cutouts in the back panel

    snap_cut_radius = snap_fit_radius_mm+(snap_fit_gap_mm/2.0)

    snap_fit_width = inner_holder_back_width_mm -(2*(snap_fit_slot_margin_mm-snap_fit_slot_extend_mm))

    snap_fit_cut = Part.makeCylinder(snap_cut_radius,snap_fit_width,
        App.Vector(inner_border_x+snap_fit_slot_margin_mm-snap_fit_slot_extend_mm,
            inner_border_y,
            outer_holder_back_thickness_mm/2.0), # origin
        App.Vector(1,0,0))

    holder=holder.cut(snap_fit_cut)

    snap_fit_cut.translate(App.Vector(0,inner_holder_back_depth_mm,0))

    holder=holder.cut(snap_fit_cut)

    snap_fit_depth = inner_holder_back_depth_mm - (2*(snap_fit_slot_margin_mm-snap_fit_slot_extend_mm))

    snap_fit_cut = Part.makeCylinder(snap_cut_radius,snap_fit_depth,
        App.Vector(inner_border_x,inner_border_y+snap_fit_slot_margin_mm-snap_fit_slot_extend_mm,outer_holder_back_thickness_mm/2.0), # origin
        App.Vector(0,1,0))

    holder=holder.cut(snap_fit_cut)

    snap_fit_cut.translate(App.Vector(inner_holder_back_width_mm,0,0))

    holder=holder.cut(snap_fit_cut)

    holder.translate(App.Vector(0,0,
        letter_cell_base_thickness_mm+separator_thickness_mm+led_panel_thickness_mm))

    # create the snap fit cylinders and add them to the front panel

    snap_fit_width = (grid_width_mm+(2*letter_grid_border_mm)) - (2*snap_fit_slot_margin_mm)

    snap_fit_fuse = Part.makeCylinder(snap_fit_radius_mm,snap_fit_width,
        App.Vector(outer_frame_size_mm+snap_fit_slot_margin_mm,
            outer_frame_size_mm+letter_grid_border_mm-snap_fit_radius_mm,
            surround_thick-(outer_holder_back_thickness_mm/2.0)), # origin
            App.Vector(1,0,0))

    panel = panel.fuse(snap_fit_fuse)

    snap_fit_fuse.translate(App.Vector(0,grid_depth_mm+(2*letter_grid_border_mm),0))

    panel = panel.fuse(snap_fit_fuse)

    snap_fit_depth = (grid_depth_mm+(2*letter_grid_border_mm)) - (2*snap_fit_slot_margin_mm)

    snap_fit_fuse = Part.makeCylinder(snap_fit_radius_mm,snap_fit_depth,
        App.Vector(outer_frame_size_mm,
            outer_frame_size_mm+letter_grid_border_mm-snap_fit_radius_mm+snap_fit_slot_margin_mm,
            surround_thick-(outer_holder_back_thickness_mm/2.0)), # origin
            App.Vector(0,1,0))

    panel = panel.fuse(snap_fit_fuse)

    snap_fit_fuse.translate(App.Vector(grid_width_mm+(2*letter_grid_border_mm),0,0))

    panel = panel.fuse(snap_fit_fuse)
    
# Display everything
    
    panel_obj = doc.addObject("Part::Feature", "Panel")
    panel_obj.ViewObject.ShapeColor = (0.9, 0.9, 0.1)   # fill colour
    panel_obj.Shape = panel

    solid_obj = doc.addObject("Part::Feature", "Solid")
    solid_obj.ViewObject.ShapeColor = (0.1, 0.1, 0.1)   # fill colour
    solid_obj.Shape = solid_grid

    # Move the separator back so that it fits behind the letter grid
    separator.translate(App.Vector(0,0,letter_cell_base_thickness_mm))

    separator_obj = doc.addObject("Part::Feature", "separator")
    separator_obj.ViewObject.ShapeColor = (0.9, 0.1, 0.9)   # fill colour
    separator_obj.Shape = separator

    leds_obj = doc.addObject("Part::Feature", "leds")
    leds_obj.ViewObject.ShapeColor = (0.9, 0.1, 0.1)   # fill colour
    leds_obj.Shape = leds

    holder_obj = doc.addObject("Part::Feature", "holder")
    holder_obj.ViewObject.ShapeColor = (0.9, 0.1, 0.9)   # fill colour
    holder_obj.Shape = holder

    pico_obj = doc.addObject("Part::Feature", "pico")
    pico_obj.ViewObject.ShapeColor = (0.1, 0.7, 0.9)   # fill colour
    pico_obj.Shape = pico



if not os.path.exists(json_path):
    raise FileNotFoundError(f"Cannot find wordsearch JSON at: {json_path}")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

name = data["name"]
grid = data["grid"]
rows = grid["letters"]
row_count = grid["rows"]
col_count = grid["cols"]
placements = data["words"]

#name = data.get("name", "Wordsearch")
#grid = data.get
#rows = data.get("grid.letters", [])
#row_count = data.get("grid.rows", len(rows))
#col_count = data.get("grid.cols", len(rows[0]) if rows else 0)
#placements = data.get("words", [])

FreeCAD.Console.PrintMessage(f"\nLoaded '{name}' ({col_count}x{row_count})\n")


# design for through hole letters
#make_grid(grid=rows,engrave_letters=True,no_letters_on_tiles=False,letter_cell_base_thickness_mm=2.0,letter_thickness_mm=2.0,behind_letter_panel_thickness=0.5)

# design for obscured letters
#make_grid(grid=rows,engrave_letters=True,no_letters_on_tiles=False)

# Test design for making quick boxes to check layout
make_grid(grid=rows,engrave_letters=True,no_letters_on_tiles=True,letter_cell_base_thickness_mm=2.0,letter_thickness_mm=2.0,behind_letter_panel_thickness=0.5,speaker=True)

if firstRun:
    Gui.ActiveDocument.ActiveView.fitAll()
    
