# Edit these appropriately before running this script
maj=5
min=6
rev=0
branchname=release-pypy2.7-5.x # ==OR== release-$maj.x  # ==OR== release-$maj.$min.x
tagname=release-pypy2.7-v$maj.$min.$rev  # ==OR== release-$maj.$min

echo checking hg log -r $branchname
hg log -r $branchname || exit 1
echo checking hg log -r $tagname
hg log -r $tagname || exit 1

rel=pypy2-v$maj.$min.$rev
# This script will download latest builds from the buildmaster, rename the top
# level directory, and repackage ready to be uploaded to bitbucket. It will also
# download source, assuming a tag for the release already exists, and repackage them.
# The script should be run in an empty directory, i.e. /tmp/release_xxx
for plat in linux linux64 linux-armhf-raspbian linux-armhf-raring linux-armel osx64 s390x
  do
    echo downloading package for $plat
    wget http://buildbot.pypy.org/nightly/$branchname/pypy-c-jit-latest-$plat.tar.bz2
    tar -xf pypy-c-jit-latest-$plat.tar.bz2
    rm pypy-c-jit-latest-$plat.tar.bz2
    plat_final=$plat
    if [ $plat = linux ]; then
        plat_final=linux32
    fi
    mv pypy-c-jit-*-$plat $rel-$plat_final
    echo packaging $plat_final
    tar --owner=root --group=root --numeric-owner -cjf $rel-$plat_final.tar.bz2 $rel-$plat_final
    rm -rf $rel-$plat_final
  done

plat=win32
wget http://buildbot.pypy.org/nightly/$branchname/pypy-c-jit-latest-$plat.zip
unzip pypy-c-jit-latest-$plat.zip
rm pypy-c-jit-latest-$plat.zip
mv pypy-c-jit-*-$plat $rel-$plat
zip -rq $rel-$plat.zip $rel-$plat
rm -rf $rel-$plat

# Requires a valid $tagname, note the untarred directory is pypy-pypy-<hash>
# so make sure there is not another one
wget https://bitbucket.org/pypy/pypy/get/$tagname.tar.bz2
tar -xf $tagname.tar.bz2
rm $tagname.tar.bz2
mv pypy-pypy-* $rel-src
tar --owner=root --group=root --numeric-owner -cjf $rel-src.tar.bz2 $rel-src
zip -rq $rel-src.zip $rel-src
rm -rf $rel-src

# Print out the md5, sha1, sha256
md5sum *.bz2 *.zip
sha1sum *.bz2 *.zip
sha256sum *.bz2 *.zip

# Now upload all the bz2 and zip


