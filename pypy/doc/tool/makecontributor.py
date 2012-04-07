import py
import sys
from collections import defaultdict
import operator
import re
import mercurial.localrepo
import mercurial.ui

ROOT = py.path.local(__file__).join('..', '..', '..', '..')
author_re = re.compile('(.*) <.*>')

excluded = set(["pypy" "convert-repo"])

alias = {
    'arigo': 'Armin Rigo',
    'lac': 'Laura Creighton',
    'fijal': 'Maciej Fijalkowski',
    'tismer@christia-wjtqxl.localdomain': 'Christian Tismer',
    'holger krekel': 'Holger Krekel',
    'hager': 'Sven Hager',
    'mattip': 'Matti Picus',
    'mattip>': 'Matti Picus',
    'matthp': 'Matti Picus',
    'Matti Picus matti.picus@gmail.com': 'Matti Picus',
    'edelsohn': 'David Edelsohn',
    'edelsoh': 'David Edelsohn',
    'l.diekmann': 'Lukas Diekmann',
    'ldiekmann': 'Lukas Diekmann',
    'aliles': 'Aaron Iles',
    'mikefc': 'Michael Cheng',
    'cocoatomo': 'Tomo Cocoa',
    'roberto@goyle': 'Roberto De Ioris',
    'roberto@mrspurr': 'Roberto De Ioris',
    'landtuna@gmail.com': 'Jim Hunziker',
    'kristjan@kristjan-lp.ccp.ad.local': 'Kristjan Valur Jonsson',
    }

def get_canonical_author(name):
    match = author_re.match(name)
    if match:
        name = match.group(1)
    return alias.get(name, name)

def main(show_numbers):
    ui = mercurial.ui.ui()
    repo = mercurial.localrepo.localrepository(ui, str(ROOT))
    authors = defaultdict(int)
    for i in repo:
        ctx = repo[i]
        author = get_canonical_author(ctx.user())
        if author not in excluded:
            authors[author] += 1
    #
    items = authors.items()
    items.sort(key=operator.itemgetter(1), reverse=True)
    for name, n in items:
        if show_numbers:
            print '%5d %s' % (n, name)
        else:
            print name

if __name__ == '__main__':
    show_numbers = '-n' in sys.argv
    main(show_numbers)
