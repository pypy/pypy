# -*- coding: utf-8 -*-
from os import path

from pypy.module.cpyext import api

from sphinx import addnodes


TEMPLATE = """
@cpython_api([%(paramtypes)s], %(rettype)s)
def %(functionname)s(%(params)s):
%(docstring)s    raise NotImplementedError
    %(borrows)s
"""

C_TYPE_TO_PYPY_TYPE = {
        "void": "lltype.Void",
        "int": "rffi.INT_real",
        "PyTypeObject*": "PyTypeObjectPtr",
        "PyVarObject*": "PyObject",
        "const char*": "rffi.CCHARP",
        "double": "rffi.DOUBLE",
        "PyObject*": "PyObject",
        "PyObject**": "PyObjectP",
        "char*": "rffi.CCHARP",
        "PyMethodDef*": "PyMethodDef",
        "Py_ssize_t": "Py_ssize_t",
        "Py_ssize_t*": "Py_ssize_t",
        "size_t": "rffi.SIZE_T",
        "...": "...",
        "char": "lltype.Char",
        "long": "lltype.Signed",
        "Py_buffer*": "Py_buffer",
        "": "",
        }

C_TYPE_TO_PYPY_TYPE_ARGS = C_TYPE_TO_PYPY_TYPE.copy()
C_TYPE_TO_PYPY_TYPE_ARGS.update({
    "void": "rffi.VOIDP",
    })


def c_param_to_type_and_name(string, is_arg=True):
    string = string.replace(" **", "** ").replace(" *", "* ")
    try:
        typ, name = string.rsplit(" ", 1)
    except ValueError:
        typ = string
        name = ""
    return [C_TYPE_TO_PYPY_TYPE, C_TYPE_TO_PYPY_TYPE_ARGS][is_arg]\
            .get(typ, "{" + typ + "}"), name


def process_doctree(app, doctree):
    for node in doctree.traverse(addnodes.desc_content):
        par = node.parent
        if par['desctype'] != 'cfunction':
            continue
        if not par[0].has_key('names') or not par[0]['names']:
            continue
        functionname = par[0]['names'][0]
        if (functionname in api.FUNCTIONS or
            functionname in api.SYMBOLS_C):
            print "Wow, you implemented already", functionname
            continue
        borrows = docstring = ""
        crettype, _, cparameters = par[0]
        crettype = crettype.astext()
        cparameters = cparameters.astext()
        rettype, _ = c_param_to_type_and_name(crettype, False)
        params = ["space"]
        paramtypes = []
        for param in cparameters.split(","):
            typ, name = c_param_to_type_and_name(param.strip())
            params.append(name)
            paramtypes.append(typ)
        params = ", ".join(params)
        paramtypes = ", ".join(paramtypes)
        docstring = node.astext()
        entry = app._refcounts.get(functionname)
        if entry and entry.result_type in ("PyObject*", "PyVarObject*"):
            if entry.result_refs is None:
                docstring += "\nReturn value: always NULL."
            else:
                borrows = ("borrow_from()", "")[entry.result_refs]
        docstring = "\n    ".join(docstring.splitlines())
        if docstring:
            docstring = '    """%s"""\n' % (docstring,)
        code = TEMPLATE % locals()
        app._stubgen_f.write(code)


def init_apidump(app):
    fname = path.join(path.dirname(api.__file__), "stubs.py")
    app._stubgen_f = file(fname, "w")
    app.connect('doctree-read', process_doctree)


def setup(app):
    app.connect('builder-inited', init_apidump)
