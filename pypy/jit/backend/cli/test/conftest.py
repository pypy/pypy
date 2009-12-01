import py

class Directory(py.test.collect.Directory):
    def collect(self):
        py.test.skip("CLI backend tests skipped for now")
