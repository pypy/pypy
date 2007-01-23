import autopath
import py
from pypy.config import pypyoption, translationoption, config
from pypy.doc.config.confrest import all_optiondescrs

thisdir = py.magic.autopath().dirpath()

for descr in all_optiondescrs:
    prefix = descr._name
    c = config.Config(descr)
    thisdir.join(prefix + ".txt").ensure()
    for p in c.getpaths(include_groups=True):
        basename = prefix + "." + p + ".txt"
        f = thisdir.join(basename)
        f.ensure()
