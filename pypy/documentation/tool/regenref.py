
import py
py.magic.autopath()
import pypy
base = py.path.local(pypy.__file__).dirpath()
target = base.join('documentation', '_ref.txt') 

def match(p): 
    return p.relto(base).count(p.sep) < 2 \
           and p.check(dir=1, dotfile=0) \
           and p.basename not in ('test', '_cache') 

items = []
for dir in base.visit(match, lambda x: x.check(dotfile=0) and x.basename != '_cache'): 
    assert dir.basename != '_cache'
    items.append(dir.relto(base)+dir.sep)
    for fn in dir.listdir(lambda x: x.check(file=1, ext='.py')): 
        assert fn.basename != '_cache'
        items.append(fn.relto(base))

items.sort()

lines = [] 
for x in items: 
    lines.append(".. _`%s`: http://codespeak.net/svn/pypy/dist/pypy/%s" %(x,x,))

lines.append("")
for x in base.listdir(match): 
    x = x.relto(base)
    lines.append(".. _`pypy/%s/`: http://codespeak.net/svn/pypy/dist/pypy/%s" %(x,x))

target.write("\n".join(lines))
