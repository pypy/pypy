from pypy.translator.geninterplevel import translate_as_module, __file__ as __
from pypy.objspace.std import Space
import os
fname = os.path.join(os.path.dirname(__), "test", "rpystone.py")
src = file(fname).read()
init, ign = translate_as_module(src)#, tmpname="/tmp/look.py")

LOOPS = 25

def test_rpystone():
    space = Space()
    modic = init(space)
    entry = space.getitem(modic, space.wrap("entrypoint"))
    # warm-up,to get everything translated
    space.call(entry, space.newtuple([space.wrap(-1)]))
    # now this is the real one
    space.call(entry, space.newtuple([space.wrap(LOOPS)]))

if __name__ == "__main__":
    test_rpystone()