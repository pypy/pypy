from pypy.objspace.std.objspace import *

appfile = StdObjSpace.AppFile(__name__)
W_SequenceIterator = pull_class_from_appfile(appfile, 'SequenceIterator')

StdObjSpace.getiter.register(W_SequenceIterator.method('__iter__'),
                             W_SequenceIterator....)


# XXX figure out some nice syntax to grab multimethods from the _app.py file
