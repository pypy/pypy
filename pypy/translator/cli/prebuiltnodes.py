from pypy.translator.cli.function import Function

try:
    set
except NameError:
    from sets import Set as set

class Helper(Function):
    def render(self, ilasm):
        ilasm.begin_namespace('pypy.runtime')
        ilasm.begin_class('Helpers')
        Function.render(self, ilasm)
        ilasm.end_class()
        ilasm.end_namespace()

def raise_RuntimeError():
    raise RuntimeError

def raise_OverflowError():
    raise OverflowError

def raise_ValueError():
    raise ValueError

def raise_ZeroDivisionError():
    raise ZeroDivisionError

def raise_UnicodeDecodeError():
    raise UnicodeDecodeError

HELPERS = [(raise_RuntimeError, []),
           (raise_OverflowError, []),
           (raise_ValueError, []),
           (raise_ZeroDivisionError, []),
           (raise_UnicodeDecodeError, []),
           ]

def _build_helpers(translator, db):
    functions = set()
    for fn, annotation in HELPERS:
        functions.add(fn)
        translator.annotator.build_types(fn, annotation)
    translator.rtyper.specialize_more_blocks()

    res = []
    for graph in translator.graphs:
        func = getattr(graph, 'func', None)
        if func in functions:
            res.append(Helper(db, graph, func.func_name))
    return res


def get_prebuilt_nodes(translator, db):
    prebuilt_nodes = _build_helpers(translator, db)
    raise_OSError_graph = translator.rtyper.exceptiondata.fn_raise_OSError.graph
    prebuilt_nodes.append(Helper(db, raise_OSError_graph, 'raise_OSError'))

    try:
        etrafo = db.exceptiontransformer
    except AttributeError:
        pass
    else:
        for name in ('rpyexc_clear',
                     'rpyexc_fetch_type',
                     'rpyexc_fetch_value',
                     'rpyexc_occured',
                     'rpyexc_raise'):
            sm = getattr(etrafo, name+'_ptr').value
            prebuilt_nodes.append(Function(db, sm.graph, name))
    return prebuilt_nodes
