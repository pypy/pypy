import sys, os
import importlib.machinery, importlib.util

__path__ = [ ]

class Loader(object):
    def __init__(self, fullname, filename):
        self.fullname = fullname
        self.filename = filename

    def load_module(self, fullname):
        # replaces imp.load_module, removed in 3.12
        loader = importlib.machinery.SourceFileLoader(fullname, self.filename)
        spec = importlib.util.spec_from_file_location(
            fullname, self.filename, loader=loader)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = mod
        loader.exec_module(mod)
        mod.__loader__ = self  # for introspection
        return mod

class Importer(object):
    def __init__(self, path):
        if path not in __path__:
            raise ImportError

    def find_spec(self, fullname, target=None):
        if not fullname.startswith('hooktest'):
            return None

        _, mod_name = fullname.rsplit('.', 1)
        # replaces imp.find_module, removed in 3.12
        for entry in __path__:
            for suffix in importlib.machinery.SOURCE_SUFFIXES:
                filename = os.path.join(entry, mod_name + suffix)
                if os.path.exists(filename):
                    return importlib.util.spec_from_loader(
                        fullname, Loader(fullname, filename))
        return None
