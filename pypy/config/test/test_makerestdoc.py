from pypy.config.config import *
import pypy.config.makerestdoc

from py.__.doc.conftest import restcheck

tempdir = py.test.ensuretemp('config')

def checkrest(rest, filename):
    tempfile = tempdir.join(filename)
    tempfile.write(rest)
    restcheck(tempfile)
    return tempfile.new(ext='.html').read()

def test_simple():
    descr = OptionDescription("foo", "doc", [
            ChoiceOption("bar", "more doc", ["a", "b", "c"]),
            OptionDescription("sub", "nope", [
                ChoiceOption("subbar", "", ["d", "f"])])])
    config = Config(descr)
    txt = descr.make_rest_doc().text()
    checkrest(txt, descr._name + ".txt")
    for path in config.getpaths(include_groups=True):
        subconf, step = config._cfgimpl_get_home_by_path(path)
        fullpath = (descr._name + "." + path)
        prefix = fullpath.rsplit(".", 1)[0]
        txt = getattr(subconf._cfgimpl_descr, step).make_rest_doc(
                prefix).text()
        checkrest(txt, fullpath + ".txt")
