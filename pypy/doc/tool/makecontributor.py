# NOTE: run this script with LANG=en_US.UTF-8

import py
import sys
from collections import defaultdict
import operator
import re
import mercurial.localrepo
import mercurial.ui

ROOT = py.path.local(__file__).join('..', '..', '..', '..')
author_re = re.compile('(.*) <.*>')
pair_programming_re = re.compile(r'^\((.*?)\)')
excluded = set(["pypy", "convert-repo"])

alias = {
    'Anders Chrigstrom': ['arre'],
    'Antonio Cuni': ['antocuni', 'anto'],
    'Armin Rigo': ['arigo', 'arfigo', 'armin', 'arigato'],
    'Maciej Fijalkowski': ['fijal'],
    'Carl Friedrich Bolz': ['cfbolz', 'cf'],
    'Samuele Pedroni': ['pedronis', 'samuele', 'samule'],
    'Michael Hudson': ['mwh'],
    'Holger Krekel': ['hpk', 'holger krekel', 'holger', 'hufpk'],
    "Amaury Forgeot d'Arc": ['afa'],
    'Alex Gaynor': ['alex', 'agaynor'],
    'David Schneider': ['bivab', 'david'],
    'Christian Tismer': ['chris', 'christian', 'tismer',
                         'tismer@christia-wjtqxl.localdomain'],
    'Benjamin Peterson': ['benjamin'],
    'Hakan Ardo': ['hakan', 'hakanardo'],
    'Niklaus Haldimann': ['nik'],
    'Alexander Schremmer': ['xoraxax'],
    'Anders Hammarquist': ['iko'],
    'David Edelsohn': ['edelsoh', 'edelsohn'],
    'Niko Matsakis': ['niko'],
    'Jakub Gustak': ['jlg'],
    'Guido Wesdorp': ['guido'],
    'Michael Foord': ['mfoord'],
    'Mark Pearse': ['mwp'],
    'Toon Verwaest': ['tverwaes'],
    'Eric van Riet Paap': ['ericvrp'],
    'Jacob Hallen': ['jacob', 'jakob'],
    'Anders Lehmann': ['ale', 'anders'],
    'Bert Freudenberg': ['bert'],
    'Boris Feigin': ['boris', 'boria'],
    'Valentino Volonghi': ['valentino', 'dialtone'],
    'Aurelien Campeas': ['aurelien', 'aureliene'],
    'Adrien Di Mascio': ['adim'],
    'Jacek Generowicz': ['Jacek', 'jacek'],
    'Jim Hunziker': ['landtuna@gmail.com'],
    'Kristjan Valur Jonsson': ['kristjan@kristjan-lp.ccp.ad.local'],
    'Laura Creighton': ['lac'],
    'Aaron Iles': ['aliles'],
    'Ludovic Aubry': ['ludal', 'ludovic'],
    'Lukas Diekmann': ['l.diekmann', 'ldiekmann'],
    'Matti Picus': ['Matti Picus matti.picus@gmail.com',
                    'matthp', 'mattip', 'mattip>'],
    'Michael Cheng': ['mikefc'],
    'Richard Emslie': ['rxe'],
    'Roberto De Ioris': ['roberto@goyle'],
    'Roberto De Ioris': ['roberto@mrspurr'],
    'Sven Hager': ['hager'],
    'Tomo Cocoa': ['cocoatomo'],
    'Romain Guillebert': ['rguillebert', 'rguillbert', 'romain', 'Guillebert Romain'],
    'Ronan Lamy': ['ronan'],
    'Edd Barrett': ['edd'],
    'Manuel Jacob': ['mjacob'],
    'Rami Chowdhury': ['necaris'],
    }

alias_map = {}
for name, nicks in alias.iteritems():
    for nick in nicks:
        alias_map[nick] = name

def get_canonical_author(name):
    match = author_re.match(name)
    if match:
        name = match.group(1)
    return alias_map.get(name, name)

ignored_nicknames = defaultdict(int)

def get_more_authors(log):
    match = pair_programming_re.match(log)
    if not match:
        return set()
    ignore_words = ['around', 'consulting', 'yesterday', 'for a bit', 'thanks',
                    'in-progress', 'bits of', 'even a little', 'floating',
                    'a bit', 'reviewing']
    sep_words = ['and', ';', '+', '/', 'with special  by']
    nicknames = match.group(1)
    for word in ignore_words:
        nicknames = nicknames.replace(word, '')
    for word in sep_words:
        nicknames = nicknames.replace(word, ',')
    nicknames = [nick.strip().lower() for nick in nicknames.split(',')]
    authors = set()
    for nickname in nicknames:
        author = alias_map.get(nickname)
        if not author:
            ignored_nicknames[nickname] += 1
        else:
            authors.add(author)
    return authors

def main(show_numbers):
    ui = mercurial.ui.ui()
    repo = mercurial.localrepo.localrepository(ui, str(ROOT))
    authors_count = defaultdict(int)
    for i in repo:
        ctx = repo[i]
        authors = set()
        authors.add(get_canonical_author(ctx.user()))
        authors.update(get_more_authors(ctx.description()))
        for author in authors:
            if author not in excluded:
                authors_count[author] += 1

    # uncomment the next lines to get the list of nicknamed which could not be
    # parsed from commit logs
    ## items = ignored_nicknames.items()
    ## items.sort(key=operator.itemgetter(1), reverse=True)
    ## for name, n in items:
    ##     if show_numbers:
    ##         print '%5d %s' % (n, name)
    ##     else:
    ##         print name

    items = authors_count.items()
    items.sort(key=operator.itemgetter(1), reverse=True)
    for name, n in items:
        if show_numbers:
            print '%5d %s' % (n, name)
        else:
            print '  ' + name

if __name__ == '__main__':
    show_numbers = '-n' in sys.argv
    main(show_numbers)
