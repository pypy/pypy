import autopath
import pypy.translator.test.test_annrpython
parent = pypy.translator.test.test_annrpython.TestAnnonateTestCase


class TestAnnonateAndSimplifyTestCase(parent):
    """Same tests as test_annrpython.TestAnnotateTestCase, but automatically
    running the simplify() method of the annotator after the annotation phase.
    """

    class RPythonAnnotator(parent.RPythonAnnotator):
        def complete(self):
            parent.RPythonAnnotator.complete(self)
            if self.translator is not None:
                self.simplify()
