#!/usr/bin/env python

import Image
import ImageDraw
import urllib
import StringIO
import math
import sys
import colorsys

import py
pyhtml = py.xml.html


class PerfTable:
    """parses performance history data files and yields PerfResult objects
    through the get_results method.

    if an branch is given, it is used to get more information for each
    revision we have data from.
    """
    branch = None
    
    def __init__(self, iterlines = []):
        """:param iterline: lines of performance history data,
        e.g., history_file.realdlines()
        """
        self._revision_cache = {}
        self.results = list(self.parse(iterlines))
        
    def parse(self, iterlines):
        """parse lines like
        --date 1152625530.0 hacker@canonical.com-20..6dc
          1906ms bzrlib....one_add_kernel_like_tree
        """
        date = None
        revision_id = None
        for line in iterlines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('--date'):
                _, date, revision_id = line.split(None, 2)
                date = float(date)
                continue
            perfresult = PerfResult(date=date, revision_id=revision_id)
            elapsed_time, test_id = line.split(None, 1)
            perfresult.elapsed_time = int(elapsed_time[:-2])
            perfresult.test_id = test_id.strip()
            yield self.annotate(perfresult)
        
    def add_lines(self, lines):
        """add lines of performance history data """
        
        self.results += list(self.parse(lines))

    def get_time_for_revision_id(self, revision_id):
        """return the data of the revision or 0"""
        if revision_id in self._revision_cache:
            return self._revision_cache[revision_id][1].timestamp
        return 0
        
    def get_time(self, revision_id):
        """return revision date or the date of recording the
        performance history data"""
        
        t = self.get_time_for_revision_id(revision_id)
        if t: 
            return t
        result = list(self.get_results(revision_ids=[revision_id],
                                       sorted_by_rev_date=False))[0]
        return result.date
   
    count = py.std.itertools.count() 
    def annotate(self, result):
        """Try to put extra information for each revision on the
        PerfResult objects. These informations are retrieved from a
        branch object.
        """
        #if self.branch is None:
        #    return result
        class Branch:
            revision_id = result.revision_id  
            nick = "fake"
        
        self.branch = Branch()
        result.revision = self.count.next()
        result.revision_date = "01/01/2007"
        result.message = "fake log message"
        result.timestamp = 1231231.0
        return result
        

        revision_id = result.revision_id
        if revision_id in self._revision_cache:
            revision, rev, nick = self._revision_cache[revision_id]
        else:
            revision =  self.branch.revision_id_to_revno(revision_id)
            rev = self.branch.repository.get_revision(revision_id)
            nick = self.branch._get_nick()
            self._revision_cache[revision_id] = (revision, rev, nick)
            
        result.revision = revision
        result.committer = rev.committer
        result.message = rev.message
        result.timstamp = rev.timestamp
        # XXX no format_date, but probably this whole function
        # goes away soon
        result.revision_date = format_date(rev.timestamp, rev.timezone or 0)
        result.nick = nick
        return result
    
    def get_results(self, test_ids=None, revision_ids=None,
                    sorted_by_rev_date=True):
        # XXX we might want to build indexes for speed
        for result in self.results:
            if test_ids and result.test_id not in test_ids:
                continue
            if revision_ids and result.revision_id not in revision_ids:
                continue
            yield result

    def list_values_of(self, attr):
        """return a list of unique values of the specified attribute
        of PerfResult objects"""
        return dict.fromkeys((getattr(r, attr) for r in self.results)).keys()

    def get_testid2collections(self):
        """return a mapping of test_id to list of PerfResultCollection
        sorted by revision"""
        
        test_ids = self.list_values_of('test_id')
       
        testid2resultcollections = {}
        for test_id in test_ids:
            revnos = {}
            for result in self.get_results(test_ids=[test_id]): 
                revnos.setdefault(result.revision, []).append(result)
            for revno, results in revnos.iteritems():
                collection = PerfResultCollection(results)
                l = testid2resultcollections.setdefault(test_id, [])
                l.append(collection)
        # sort collection list by revision number
        for collections in testid2resultcollections.itervalues():
            collections.sort(lambda x,y: cmp(x.revision, y.revision))
        return testid2resultcollections

    
class PerfResult:
    """Holds information about a benchmark run of a particular test run."""
    
    def __init__(self, date=0.0, test_id="", revision=0.0, 
                 revision_id="NONE", timestamp=0.0,
                 revision_date=0.0, elapsed_time=-1, 
                 committer="", message="", nick=""): 
        self.__dict__.update(locals())
        del self.self

        
class PerfResultCollection(object):
    """Holds informations about several PerfResult objects. The
    objects should have the same test_id and revision_id"""
    
    def __init__(self, results=None):
        if results is None:
            self.results = []
        else:
            self.results = results[:]
        #self.check()

    def __repr__(self):
        self.check()
        if not self.results:
            return "<PerfResultCollection EMPTY>"
        sample = self.results[0]
        return "<PerfResultCollection test_id=%s, revno=%s>" %(
               sample.test_id, sample.revision)
    
    @property   
    def min_elapsed(self):
        return self.getfastest().elapsed_time 

    def getfastest(self):
        x = None
        for res in self.results:
            if x is None or res.elapsed_time < x.elapsed_time: 
                x = res
        return x

    @property
    def test_id(self):
        # check for empty results?
        return self.results[0].test_id

    @property
    def revision_id(self):
        # check for empty results?
        return self.results[0].revision_id

    @property
    def revision(self):
        # check for empty results?
        return self.results[0].revision
           
    def check(self):
        for s1, s2 in zip(self.results, self.results[1:]):
            assert s1.revision_id == s2.revision_id 
            assert s1.test_id == s2.test_id
            assert s1.revision == s2.revision
            assert s1.date != s2.date
            
    def append(self, sample):
        self.results.append(sample)
        self.check()

    def extend(self, results):
        self.results.extend(results)
        self.check() 
        
    def __len__(self):
        return len(self.results)


class PerfResultDelta:
    """represents the difference of two PerfResultCollections"""

    def __init__(self, _from, _to=None): 
        if _from is None:
            _from = _to
        if _to is None:
            _to = _from
        if isinstance(_from, list):
            _from = PerfResultCollection(_from)
        if isinstance(_to, list):
            _to = PerfResultCollection(_to)
        assert isinstance(_from, PerfResultCollection)
        assert isinstance(_to, PerfResultCollection)
        assert _from.test_id == _to.test_id, (_from.test_id, _to.test_id)
        self._from = _from
        self._to = _to
        self.test_id = self._to.test_id
        self.delta = self._to.min_elapsed - self._from.min_elapsed 

        # percentage
        m1 = self._from.min_elapsed 
        m2 = self._to.min_elapsed 
        if m1 == 0: 
            self.percent = 0.0
        else:
            self.percent = float(m2-m1) / float(m1)


class Page:
    """generates a benchmark summary page
    The generated page is self contained, all images are inlined. The
    page refers to a local css file 'benchmark_report.css'.
    """
    
    def __init__(self, perftable=None):
        """perftable is of type PerfTable"""
        self.perftable = perftable

    def render(self):
        """return full rendered page html tree for the perftable."""
        
        perftable = self.perftable
        testid2collections = perftable.get_testid2collections()

        # loop to get per-revision collection and the 
        # maximum delta revision collections. 
        maxdeltas = []
        revdeltas = {}
        start = end = None
        for testid, collections in testid2collections.iteritems():
            if len(collections) < 2:  # less than two revisions sampled
                continue
            # collections are sorted by lowest REVNO first 
            delta = PerfResultDelta(collections[0], collections[-1])
            maxdeltas.append(delta)

            # record deltas on target revisions
            for col1, col2 in zip(collections, collections[1:]):
                revdelta = PerfResultDelta(col1, col2)
                l = revdeltas.setdefault(col2.revision, [])
                l.append(revdelta)
            
            # keep track of overall earliest and latest revision 
            if start is None or delta._from.revision < start.revision: 
                start = delta._from.results[0]
            if end is None or delta._to.revision > end.revision:
                end = delta._to.results[0]

        # sort by best changes first 
        maxdeltas.sort(key=lambda x: x.percent)

        # generate revision reports
        revno_deltas = revdeltas.items()
        revno_deltas.sort()
        revno_deltas.reverse()
        revreports = []
        for revno, deltas in revno_deltas:
            # sort by best changes first 
            deltas.sort(key=lambda x: x.percent)
            revreports.append(self.render_report(deltas))
        assert revreports

        # generate images
        #
        # generate the x axis, a list of revision numbers
        xaxis = perftable.list_values_of('revision')
        xaxis.sort()
        # samples of tests in the order of max_deltas test_ids
        samples = [testid2collections[delta.test_id] for delta in maxdeltas]
        # images in the order of max_deltas test_ids
        images = [self.gen_image_map(sample, xaxis) for sample in samples]

        page = pyhtml.html( 
            pyhtml.head(
                pyhtml.meta(
                    name="Content-Type", 
                    value="text/html; charset=latin1",
                    ),
                pyhtml.link(rel="stylesheet",
                            type="text/css",
                            href="benchmark_report.css")
 
                ),
            pyhtml.body(
                #self.render_header(start, end),
                self.render_table(maxdeltas, images, anchors=False), 
                *revreports
                )
            )
        return page 

    def _revision_report_name(self, sample):
        """return anchor name for reports,
        used to link from an image to a report"""
        return 'revno_%s' % (sample.revision,)

    def _revision_test_report_name(self, sample):
        """return anchor name for reports,
        used to link from an image to a report"""
        return 'revno_%s_test_id_%s' % (sample.revision, sample.test_id)

    def gen_image_map(self, samples, revisions=[]):
        """return a tuple of an inlined image and the corresponding image map
        samples is a list of PerfResultCollections
        revisions is a list of revision numbers and represents the x
        axis of the graph"""

        revision2collection = dict(((s.revision, s) for s in samples))
        revision2delta = dict()
        for col1, col2 in zip(samples, samples[1:]):
            revision2delta[col2.revision] = PerfResultDelta(col1, col2)
        max_value = max([s.min_elapsed for s in samples])
        map_name = samples[0].test_id # link between the image and the image map
        if max_value == 0:
            #nothing to draw
            return (pyhtml.span('No value greater than 0'), py.html.span(''))
        
        step = 3 # pixels for each revision on x axis 
        xsize = (len(revisions) - 1) * step +2
        ysize = 32 # height of the image
        im = Image.new("RGB", (xsize + 2, ysize), 'white')
        draw = ImageDraw.Draw(im)
        
        areas = []
        for x, revno in enumerate(revisions):
            if revno not in revision2collection: # data for this revision?
                continue
            sample = revision2collection[revno]
            y = ysize - (sample.min_elapsed *(ysize -2)/max_value) #scale value
            #draw.line((x*step, y, (x+1)*step, y), fill="#888888")
            draw.rectangle((x*step+1, y, x*step + step -1, ysize),
                           fill="#BBBBBB")

            head_color = "#000000"
            if revno in revision2delta:
                change = revision2delta[revno].percent
                if change < -0.15:
                    head_color = "#00FF00"
                elif change > 0.15:
                    head_color = "#FF0000"
            draw.rectangle((x*step+1, y-1, x*step + step -1, y+1),
                           fill=head_color)
            
            areas.append(
                pyhtml.area(
                    shape="rect",
                    coords= '%s,0,%s,%s' % (x*step, (x+1)*step, ysize),
                    href='#%s' % (self._revision_test_report_name(sample),),
                    title="%s Value: %s" % (sample.revision,sample.min_elapsed)
                ))
        del draw
        
        f = StringIO.StringIO()
        im.save(f, "GIF")
        image_src = 'data:image/gif,%s' % (urllib.quote(f.getvalue()),)
        html_image = pyhtml.img(src=image_src,
                                alt='Benchmark graph of %s' % (self._test_id(
                                                                       sample)),
                                usemap='#%s' % (map_name,))
        html_map = pyhtml.map(areas, name=map_name)
        return html_image, html_map
 
    def _color_for_change(self, delta, max_value=20):
        """return green for negative change_in_percent and red for
        positve change_in_percent. If change_in_percent equals 0, then
        grey is returned.
        
         The colors range from light green to full saturated green and
        light red to full saturated red.  Full saturation is reached
        when change_in_percent >= max_value.
        """
        #rgb values are between 0 and 255
        #hsv values are between 0 and 1
        if len(delta._from) < 3 or len(delta._to) < 3:
            return  '#%02x%02x%02x' % (200,200,200) # grey
            
        change_in_percent = delta.percent * 100
        if change_in_percent < 0:
            basic_color = (0,1,0) # green
        else:
            basic_color = (1,0,0) # red

        max_value = 20
        change = min(abs(change_in_percent), max_value)
        
        h,s,v = colorsys.rgb_to_hsv(*basic_color)
        rgb = colorsys.hsv_to_rgb(h, float(change) / max_value, 255)
        return '#%02x%02x%02x' % rgb

    def _change_report(self, delta): 
        """return a red,green or gray colored html representation of a
        PerfResultDelta object.
        """
          
        fromtimes = [x.elapsed_time for x in delta._from.results]
        totimes = [x.elapsed_time for x in delta._to.results]
        
        results = pyhtml.div(
            "r%d [%s] -> r%d[%s]" %(delta._from.revision, 
                                    ", ".join(map(str, fromtimes)),
                                    delta._to.revision,
                                    ", ".join(map(str, totimes)))
        )
        return pyhtml.td(
            pyhtml.div(
                '%+.1f%% change [%.0f - %.0f = %+.0f ms]' %(
                delta.percent * 100, 
                delta._to.min_elapsed, 
                delta._from.min_elapsed,
                delta.delta),
                style= "background-color: %s" % (
                        self._color_for_change(delta)),
            ),
            results,
        )

    def render_revision_header(self, sample):
        """return a header for a report with informations about
        committer, messages, revision date.
        """
        revision_id = pyhtml.li('Revision ID: %s' % (sample.revision_id,))
        revision = pyhtml.li('Revision: %s' % (sample.revision,))
        date = pyhtml.li('Date: %s' % (sample.revision_date,))
        logmessage = pyhtml.li('Log Message: %s' % (sample.message,))
        committer = pyhtml.li('Committer: %s' % (sample.committer,))
        return pyhtml.ul([date, committer, revision, revision_id, logmessage])

    def render_report(self, deltas):
        """return a report table with header. 
        
        All deltas must have the same revision_id."""
        deltas = [d for d in deltas if d.test_id]
        
        sample = deltas[0]._to.getfastest()
        report_list = self.render_revision_header(sample)

        table = self.render_table(deltas)
        return pyhtml.div(
            pyhtml.a(name=self._revision_report_name(sample)),
            report_list,
            table,
        )
    
    def render_header(self, start, end):
        """return the header of the page, sample output:
        
        benchmarks on bzr.dev
        from r1231 2006-04-01
        to r1888 2006-07-01
        """
        return [
            pyhtml.div(
                'Benchmarks for %s' % (start.nick,),
                class_="titleline maintitle",
            ),
            pyhtml.div(
                'from r%s %s' % (
                    start.revision,
                    start.revision_date,
                ),
                class_="titleline",
            ),
            pyhtml.div(
                'to r%s %s' % (
                    end.revision,
                    end.revision_date,
                ),
                class_="titleline",
            ),
        ]

    def _test_id(self, sample):
        """helper function, return a short form of a test_id """
        return '.'.join(sample.test_id.split('.')[-2:])
    
    def render_table(self, deltas, images=None, anchors=True):
        """return an html table for deltas and images. 

        this function is used to generate the main table and
        the table of each report"""
        
        classname = "main"
        if images is None:
            classname = "report"
            images = [None] * len(deltas)

        table = []
        for delta, image in zip(deltas, images):
            row = []
            anchor = ''
            if anchors:
                anchor = pyhtml.a(name=self._revision_test_report_name(
                                           delta._to.getfastest()))
            row.append(pyhtml.td(anchor, self._test_id(delta._to.getfastest()),
                                 class_='testid'))
            if image:
                row.append(pyhtml.td(pyhtml.div(*image)))
            row.append(self._change_report(delta))
            table.append(pyhtml.tr(*row))
        return pyhtml.table(border=1, class_=classname, *table)


def main(path_to_perf_history='../.perf_history'):
    try:
        perftable = PerfTable(file(path_to_perf_history).readlines())
    except IOError:
        print 'Cannot find a data file. Please specify one.'
        sys.exit(-1)
    page = Page(perftable).render()
    f = file('benchmark_report.html', 'w')
    try:
        f.write(page.unicode(indent=2).encode('latin-1'))
    finally:
        f.close()
    
if __name__ == '__main__':
    if len(sys.argv) == 1:
        main()
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv ) == 3:
        main(*sys.argv[1:3])
    else:
        print 'Usage: benchmark_report.py [perf_history [branch]]'
        
