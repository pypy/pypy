import os
from StringIO import StringIO

True,False = (1==1),(0==1)

def FileToolsError(Exception): pass

def copy(outFile='',outStream=None,inFile='',inString='',inStream=None):
    """synopsis:copy(outFile='',outStream=None,inFile='',inString='',inStream=None)
       If streams (file handles) are used, they are NOT closed by copy."""

    if inFile:
        fs = open(inFile)
    elif inString:
        fs = StringIO(inString)
    elif inStream is not None:
        fs = inStream
    else:
        raise FileToolsError('copy need valid input source (string, stream, filename)')

    if outFile:
        if os.path.isfile(outFile):
            #errorMsg = 'copy: the destination file %s exists already' % outFile
            #raise FileToolsError(errorMsg)
            pass
        of = open(outFile,'w')
    elif outStream:
        of = outStream
    else:
        raise FileToolsError('copy need valid output source (stream, filename)')

    cs = 1024
    tmp = fs.read(cs)
    while tmp:
        of.write(tmp)
        tmp = fs.read(cs)

    # only close I/O streams if they were opened in function
    if inFile:
        fs.close()
    if outFile:
        of.close()

###################################################
# simple RCS wrapper
###################################################

RCSPATH = "/usr/bin"
CI = os.path.join(RCSPATH,"ci")
CO = os.path.join(RCSPATH,"co")
RLOG = os.path.join(RCSPATH,"rlog")
RDIFF = os.path.join(RCSPATH,"rcsdiff")
RMERGE = os.path.join(RCSPATH,"rcsmerge")
WLEN = len("revision")

class PyRCSError(Exception):pass
class PyRCSFileNotBoundError(PyRCSError):pass

class PyRCS:
    """PyRCS is a thin python wrapper for the RCS versioning system. Only a few RCS
       features can be accessed."""

    def __init__(self,fileName=None,user="UnknownUser"):
        if fileName is not None:
            if not os.path.isfile(fileName):
                raise PyRCSFileNotBoundError("init: fileName %s was given but does not exist" % fileName)
            if not os.path.isfile(fileName+',v'):
                os.popen(CI + " -l -t-newFile -w%s %s" % (user,fileName))
        self._fileName = fileName
        self._user = user

    def move(self,newName):
        if self._fileName is None:
            raise PyRCSFileNotBoundError("fileName is None")
        try:
            copy(outFile=newName,inFile=self._fileName)
        except FileToolsError:
            raise PyRCSError("Couldn't move %s" % self._fileName)
        try:
            copy(outFile=newName+',v',inFile=self._fileName+',v')
        except FileToolsError:
            os.unlink(newName)
            raise PyRCSError("Couldn't move %s" % self._fileName+',v')
        os.unlink(self._fileName)
        os.unlink(self._fileName+',v')
        self._fileName = newName


    def get(self,version=""):
        if self._fileName is None:
            raise PyRCSFileNotBoundError()

        outStream = StringIO()
        copy(inStream=os.popen(CO +" -p%s %s" % (version,self._fileName)),outStream=outStream)
        outStream.seek(0)

        return outStream

    def getDiff(self,v1="",v2=""):
        if self._fileName is None:
            raise PyRCSFileNotBoundError()

        outStream = StringIO()
        copy(inStream=os.popen(RDIFF +" -r%s -r%s %s" % (v1,v2,self._fileName)),outStream=outStream)
        outStream.seek(0)

        return outStream

    def user(self,user=None):
        if user != None:
            self._user = user

        return self._user
        
    def goBack(self):
        lst = self.getVersions()
        if len(lst) < 2:
            return False
        currVer = lst[0][0]
        prevVer = lst[1][0]
        res = os.system(RMERGE + " -r%s -r%s %s" % (currVer,prevVer,self._fileName))
        if not res:
            os.popen(CI + " -l -mbackToPrevVersion -w%s %s" % (self._user,self._fileName))
            return True
        else:
            inStream = self.get(currVer)
            copy(outFile=self._fileName,inStream = inStream)
            return False

        
    def update(self,inStream):
        copy(outFile=self._fileName,inStream = inStream)
        os.popen(CI + " -l -mnewVersion -w%s %s" % (self._user,self._fileName))

    def new(self,fileName,inStream):
        self._fileName = fileName
        copy(outFile=self._fileName,inStream = inStream)
        os.popen(CI + " -l -t-newFile -w%s %s" % (self._user,self._fileName))

    def getVersions(self):
        if self._fileName is None:
            raise PyRCSFileNotBoundError()

        vlist = []
        out = os.popen(RLOG + " %s" % self._fileName).readlines()
        newVersion = False
        for line in out:
            if len(line) > WLEN and line[:WLEN] == "revision":
                version = line[WLEN:].strip().split()[0]
                newVersion = True
            if newVersion and line[:4] == "date":
                parts = line.split()
                date = parts[1] + " " + parts[2]
                date = date[:-1]
                author = parts[4]
                if author:
                    author = author[:-1]

                newVersion = False
                vlist.append((version,date,author))


        return vlist

if __name__ == "__main__":
    def test1():
        fileName = "testing/rcsTestFile"
        newName = "testing/movedTestFile"
        if os.path.isfile(fileName):
            os.unlink(fileName)
        if os.path.isfile(fileName+',v'):
            os.unlink(fileName+',v')
        if os.path.isfile(newName):
            os.unlink(newName)
        if os.path.isfile(newName+',v'):
            os.unlink(newName+',v')
        rcs = PyRCS()
        rcs.new(fileName,StringIO('Dies ist ein Testfile'))
        assert rcs.get().read() == 'Dies ist ein Testfile'
        versions = rcs.getVersions()
        assert len(versions) == 1
        assert versions[0][0] == '1.1'
        rcs.update(StringIO('neuer Inhalt'))
        assert rcs.get().read() == 'neuer Inhalt'
        versions = rcs.getVersions()
        print versions
        assert len(versions) == 2
        assert versions[0][0] == '1.2'
        rcs.move(newName)
        del(rcs)
        rcs = PyRCS(newName)
        assert rcs.get().read() == 'neuer Inhalt'
        versions = rcs.getVersions()
        assert len(versions) == 2
        assert versions[0][0] == '1.2'
        print rcs.getDiff('1.1','1.2').read()
        rcs.update(StringIO('dritte Version'))
        print rcs.getDiff('1.2','1.3').read()
        rcs.goBack()
        print rcs.getVersions()
        del(rcs)

    def test2():
        filename = 'testing/47244641499__Windows__5.x.txt'
        rcs = PyRCS(filename)
        print rcs.getVersions()
        text = rcs.get().read()
        print
        print text

    test2()
