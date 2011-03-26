import autopath
import py
from pypy.config import pypyoption, translationoption, config
from pypy.doc.config.confrest import all_optiondescrs

thisdir = py.path.local(__file__).dirpath()

for descr in all_optiondescrs:
    prefix = descr._name
    c = config.Config(descr)
    thisdir.join(prefix + ".rst").ensure()
    for p in c.getpaths(include_groups=True):
        basename = prefix + "." + p + ".rst"
        f = thisdir.join(basename)
        f.ensure()
