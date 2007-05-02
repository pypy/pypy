from pypy.translator.driver import TranslationDriver
from pypy.translator.cli.entrypoint import DllEntryPoint

class DllDef:
    def __init__(self, name, namespace, functions=[], classes=[]):
        self.name = name
        self.namespace = namespace
        self.functions = functions # [(function, annotation), ...]

    def add_function(self, func, inputtypes):
        self.functions.append((func, inputtypes))

    def get_entrypoint(self, bk):
        graphs = [bk.getdesc(f).cachedgraph(None) for f, _ in self.functions]
        return DllEntryPoint(self.name, graphs)

    def compile(self):
        # add all functions to the appropriate namespace
        for func, _ in self.functions:
            if not hasattr(func, '_namespace_'):
                func._namespace_ = self.namespace
        driver = TranslationDriver()
        driver.setup_library(self)
        driver.proceed(['compile_cli'])
        return driver


class MyClass:
    def __init__(self, x):
        self.x = x

    def foo(self):
        return self.x

def main():
    dll = DllDef('mylibrary', 'foo', [], [
        (MyClass, [int]),
        ])
    driver = dll.compile()
    driver.copy_cli_dll()
    

if __name__ == '__main__':
    main()
