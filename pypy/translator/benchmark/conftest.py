import py

class Directory(py.test.collect.Directory):

    def recfilter(self, path):
        # exclude the subdirectories added by 'svn co' from benchmarks.py
        return path.check(basename='test')
