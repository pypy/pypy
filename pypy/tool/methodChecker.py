import autopath
from pypy.objspace.std import Space
from pypy.interpreter.main import eval_string

class MethodChecker(object):
    """ Checks which methods are available on builtin types."""

    def __init__(self, types=(1, 1.0, "'a'", [], {}, (), None)):

        space = Space()
        str = ['-', 'Implemented']

        totalImplemented = 0
        totalNotImplemented = 0

        for oneType in types:
            subImplemented = 0
            subNotImplemented = 0

            attribArr = dir(type(oneType))
            for attrib in attribArr:
                x = space.unwrap(eval_string(
                    'hasattr(%s,"%s")\n' % (oneType, attrib),
                    '<string>', space))
                print '%-16s%-18s%s' % (type(oneType), attrib, str[x])
                if x:
                    subImplemented += 1
                    totalImplemented += 1
                else:
                    subNotImplemented += 1
                    totalNotImplemented += 1
            print
            print '    %-16s Implemented:     %3d' % (type(oneType),
                                                      subImplemented)
            print '    %-16s Not implemented: %3d' % (type(oneType),
                                                      subNotImplemented)
            print '    %-16s TOTAL:           %3d' % (
                type(oneType), subNotImplemented + subImplemented)
            print
            
        print 'TOTAL Implemented:     %3d' % totalImplemented
        print 'TOTAL Not implemented: %3d' % totalNotImplemented
        print 'GRAND TOTAL:           %3d' % (
            totalNotImplemented + totalImplemented)

if __name__ == '__main__':
    MethodChecker()
