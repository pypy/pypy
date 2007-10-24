import autopath
import py
from pypy.lang.smalltalk import squeakimage as sq
from pypy.lang.smalltalk import model as sqm

mini_image = py.magic.autopath().dirpath().dirpath().join('mini.image')

def test_miniimageexists():
    assert mini_image.check(dir=False)

def get_miniimage():
    return sq.ImageReader(sq.Stream(mini_image.open()))

def printStringsInImage():
    example = get_miniimage()
    example.initialize()
    
    image = sq.SqueakImage()
    image.from_reader(example)    
    
    for each in image.objects:
        if isinstance(each,sqm.W_BytesObject):
          print ''.join(each.bytes)

if __name__ == '__main__':
    printStringsInImage()
