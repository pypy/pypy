
import py.test.collect

class Directory(py.test.collect.Directory):
    def run(self):
        return []

