from pypy.translator.cli.function import Function

class PrebuiltGraph(Function):
    def render(self, ilasm):
        ilasm.begin_class('PrebuiltGraphs')
        Function.render(self, ilasm)
        ilasm.end_class()

## The following functions are used for construct prebuilt graphs.

## We need prebuilt graphs for force rendering of some classes
## (e.g. some kind of exception) or because they are used by pypylib
## (see the comment in src/stub/main.il).
def raiseExceptions(switch):
    if switch == 0:
        raise ValueError
    elif switch == 1:
        raise OverflowError
    else:
        raise ZeroDivisionError

def raiseOSError(errno):
    raise OSError(errno, None)

PREBUILT_GRAPHS = [(raiseExceptions, [int], PrebuiltGraph),
                   (raiseOSError, [int], PrebuiltGraph),
                   ]

def get_prebuilt_graphs(translator):
    functions = {}
    for fn, annotation, functype in PREBUILT_GRAPHS:
        functions[fn] = functype
        translator.annotator.build_types(fn, annotation)

    res = []
    for graph in translator.graphs:
        try:
            functype = functions[graph.func]
            res.append((graph, functype))
        except (AttributeError, KeyError):
            pass
    return res

