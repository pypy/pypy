import autopath
from pypy.tool.osfilewrapper import OsFileWrapper, create_wrapper
from pypy.tool.udir import udir 
import os

def test_reads():
    
    p = str(udir.join('test.dat'))

    # As we are testing file writes, only using udir to create a path 
    buf = "1234567890"
    f = open(p, "w")
    f.write(buf)
    f.close()

    for ii in range(10):
        f = create_wrapper(p, os.O_RDONLY)
        assert f.read(ii) == buf[:ii]
    
def test_writes_reads():

    # As we are testing file writes, only using udir to create a path 
    buf = "1234567890"
    for ii in range(10):
        p = str(udir.join('test.dat'))
        f1 = create_wrapper(p, os.O_WRONLY)
        f1.write(buf[:ii])
        f1.close()

        f2 = create_wrapper(p, os.O_RDONLY)
        assert f2.read(ii) == buf[:ii]
        f2.close()
