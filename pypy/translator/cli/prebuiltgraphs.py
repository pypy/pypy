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

PREBUILT_GRAPHS = [(raiseExceptions, [int]),
                   (raiseOSError, [int]),
                   ]

def get_prebuilt_graphs(translator):
    funcset = set()
    for fn, annotation in PREBUILT_GRAPHS:
        funcset.add(fn)
        translator.annotator.build_types(fn, annotation)
        
    res = []
    for graph in translator.graphs:
        if getattr(graph, 'func', None) in funcset:
            res.append(graph)
    return res

