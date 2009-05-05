import py

class Directory(py.test.collect.Directory):
    def consider_dir(self, path):
        py.test.skip("llvm-jit tests skipped")
