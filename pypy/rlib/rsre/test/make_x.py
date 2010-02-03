

g = open('x', 'w')

for i in range(100000):
    if i == 74747:
        tag = 'title'
    else:
        tag = 'titl'
    print >> g
    print >> g, '<item>'
    print >> g, '  <%s>FooBar%d</%s>' % (tag, i, tag)
    print >> g, '</item>'

g.close()
