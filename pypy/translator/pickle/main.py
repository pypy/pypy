import sys
from pypy.translator.pickle.genpickle import GenPickle
from pypy.translator.pickle.writer import Writer, TextWriter, ZipWriter
from pypy.translator.pickle.loader import Loader, TextLoader, ZipLoader

def load(fname):
    loader = _select(fname)[0]
    assert loader, 'only .py and .zip files supported'
    print "Loading:",
    def progress():
        sys.stdout.write('.')
    ret = loader(fname).load(progress)
    print
    return ret

def save(translator, fname, **objects):
    writer = _select(fname)[1]
    assert writer, 'only .py and .zip files supported'
    assert objects, 'please provide objects to be saved as keywords'
    pickler = GenPickle(translator, writer(fname))
    hold = sys.getrecursionlimit()
    if hold < 5000:
        sys.setrecursionlimit(5000)
    try:
        pickler.pickle(**objects)
    finally:
        sys.setrecursionlimit(hold)
    pickler.finish()
    return pickler  # for debugging purposes

# and that's all, folks!
# _________________________________________________________________

def _select(fname):
    name = fname.lower()
    if name.endswith('.py'):
        return TextLoader, TextWriter
    elif name.endswith('.zip'):
        return ZipLoader, ZipWriter
    else:
        return None, None

