import base64
from itertools import chain
from io import BytesIO as IO

from PIL import Image, ImageChops

from rdkit.Chem import AllChem as Chem
from rdkit.Chem import Draw

try:
    Draw.DrawingOptions.atomLabelFontFace = "DejaVu Sans"
    Draw.DrawingOptions.atomLabelFontSize = 18
except KeyError:  # Font "DejaVu Sans" is not available
    pass

try:
    # Try to import Avalon so it can be used for generation of 2d coordinates.
    from rdkit.Avalon import pyAvalonTools as pyAv
    USE_AVALON_2D = True
except ImportError:
    print("* Avalon not available. Using RDKit for 2d coordinate generation.")
    USE_AVALON_2D = False


def check_2d_coords(mol, force=False):
    """Check if a mol has 2D coordinates and if not, calculate them."""
    if not force:
        try:
            mol.GetConformer()
        except ValueError:
            force = True  # no 2D coords... calculate them

    if force:
        if USE_AVALON_2D:
            pyAv.Generate2DCoords(mol)
        else:
            mol.Compute2DCoords()


def make_transparent(img):
    img = img.convert("RGBA")
    pixdata = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            if pixdata[x, y] == (255, 255, 255, 255):
                pixdata[x, y] = (255, 255, 255, 0)
    return img


def autocrop(im, bgcolor="white"):
    if im.mode != "RGB":
        im = im.convert("RGB")
    bg = Image.new("RGB", im.size, bgcolor)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)
    return None  # no contents


def b64_mol(mol, size=300, hlsss=None):
    img_file = IO()
    if isinstance(mol, list):
        img = autocrop(Draw.MolsToGridImage(mol, size=(size, size)))
    else:
        if hlsss is not None:
            if isinstance(hlsss, str):
                hlsss = hlsss.split(",")
                atoms = set()
                for smi in hlsss:
                    m = Chem.MolFromSmiles(smi)
                    if m:
                        matches = list(chain(*mol.GetSubstructMatches(m)))
                    else:
                        matches = []
                    if len(matches) > 0:
                        atoms = atoms.union(set(matches))
            atoms = list(atoms)
        else:
            atoms = []
        try:
            img = autocrop(Draw.MolToImage(mol, size=(size, size), highlightAtoms=atoms))
        except UnicodeEncodeError:
            print(Chem.MolToSmiles(mol))
            mol = Chem.MolFromSmiles("*")
            img = autocrop(Draw.MolToImage(mol, size=(size, size)))
    img = make_transparent(img)
    img.save(img_file, format='PNG')
    b64 = base64.b64encode(img_file.getvalue())
    b64 = b64.decode()
    img_file.close()
    return b64


def mol_img_tag(mol, size=300, options=None):
    if isinstance(mol, str):  # convert from Smiles on-the-fly, when necessary
        mol = Chem.MolFromSmiles(mol)
        check_2d_coords(mol)
    tag = """<img {} src="data:image/png;base64,{}" alt="Mol"/>"""
    if options is None:
        options = ""
    img_tag = tag.format(options, b64_mol(mol, size=size))
    return img_tag
