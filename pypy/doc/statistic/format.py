import py
import datetime
import dateutil
from dateutil import parser

import pylab
import matplotlib

def get_data(p):
    data = p.readlines()
    title = data[0].strip()
    axis = data[1].strip().split(',')
    data = [convert_data(t) for t in zip(*[l.strip().split(',') for l in data[2:]])]
    return title, axis, data

def convert_data(row):
    if not row:
        return []
    first = row[0]
    try:
        int(first)
        return [int(elt) for elt in row]
    except ValueError:
        pass
    try:
        float(first)
        return [float(elt) for elt in row]
    except ValueError:
        pass
    parsedate(first)
    return [parsedate(elt) for elt in row]

def parsedate(s):
    if len(s) <= 7:
        year, month = s.split("-")
        result = datetime.datetime(int(year), int(month), 1)
    else:
        result = parser.parse(s)
    return pylab.date2num(result)

def date2str(i, dates):
    l = len(dates)
    if i == 0 or i == l-1 or i == int(l/2):
        d = dates[i]
        return str(pylab.num2date(d))[:7]
    else:
        return ""

def txt2png(p):
    print p
    title, axis, data = get_data(p)
    dates = data[0]
    line,  = pylab.plot_date(dates, data[1], "b-")
    loc, labels = pylab.xticks()
    pylab.xticks( loc, [date2str(i,dates) for i, _ in enumerate(dates)] )
    pylab.title(title)
    pylab.savefig(p.purebasename + ".png")
 
def main():
    for p in py.path.local().listdir("*.txt"):
        txt2png(p)

if __name__ == '__main__':
    main()
