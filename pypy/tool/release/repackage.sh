# Edit these appropriately before running this script
pmaj=2  # python main version: 2 or 3
pmin=7  # python minor version
maj=7
min=2
rev=0rc2

case $pmaj in
    "2") exe=pypy;;
    "3") exe=pypy3;;
    *) echo invalid pmaj=$pmaj; exit 1;;
esac

branchname=release-pypy$pmaj.$pmin-v$maj.x # ==OR== release-v$maj.x  # ==OR== release-v$maj.$min.x
tagname=release-pypy$pmaj.$pmin-v$maj.$min.$rev  # ==OR== release-$maj.$min

echo checking hg log -r $branchname
hg log -r $branchname || exit 1
echo checking hg log -r $tagname
hg log -r $tagname || exit 1
hgrev=`hg id -r $tagname -i`

rel=pypy$pmaj.$pmin-v$maj.$min.$rev
# The script should be run in an empty in the pypy tree, i.e. pypy/tmp
if [ "`ls . | wc -l`" != "0" ]
then
    echo this script must be run in an empty directory
    exit -1
fi

# Download latest builds from the buildmaster, rename the top
# level directory, and repackage ready to be uploaded to bitbucket
actual_ver=xxxxxxxxxxxxxxx
for plat in linux linux64 osx64 s390x aarch64 # linux-armhf-raspbian linux-armel
  do
    echo downloading package for $plat
    if wget -q --show-progress http://buildbot.pypy.org/nightly/$branchname/pypy-c-jit-latest-$plat.tar.bz2
    then
        echo $plat downloaded 
    else
        echo $plat no download available
        continue
    fi
    hgcheck=`tar -tf pypy-c-jit-latest-$plat.tar.bz2 |head -n1 | cut -d- -f5`
    if [ "$hgcheck" != "$hgrev" ]
    then
        echo xxxxxxxxxxxxxxxxxxxxxx
        echo $plat hg tag mismatch, expected $hgrev, got $hgcheck
        echo xxxxxxxxxxxxxxxxxxxxxx
        rm pypy-c-jit-latest-$plat.tar.bz2
        continue
    fi
    tar -xf pypy-c-jit-latest-$plat.tar.bz2
    rm pypy-c-jit-latest-$plat.tar.bz2
    plat_final=$plat
    if [ $plat = linux ]; then
        plat_final=linux32
    fi
    mv pypy-c-jit-*-$plat $rel-$plat_final
    # TODO: automate the platform choice or move it to the head of the file
    if [ $plat_final == linux64 ]
    then
        actual_ver=`$rel-$plat_final/bin/$exe -c "import sys; print('.'.join([str(x) for x in sys.pypy_version_info[:2]]))"`
    fi
    echo packaging $plat_final
    tar --owner=root --group=root --numeric-owner -cjf $rel-$plat_final.tar.bz2 $rel-$plat_final
    rm -rf $rel-$plat_final
  done
if [ "$actual_ver" != "$maj.$min" ]
then
    echo xxxxxxxxxxxxxxxxxxxxxx
    echo version mismatch, expected $maj.$min, got $actual_ver
    echo xxxxxxxxxxxxxxxxxxxxxx
    exit -1
    rm -rf $rel-$plat_final
    continue
fi
plat=win32
if wget http://buildbot.pypy.org/nightly/$branchname/pypy-c-jit-latest-$plat.zip
then
    unzip -q pypy-c-jit-latest-$plat.zip
    rm pypy-c-jit-latest-$plat.zip
    mv pypy-c-jit-*-$plat $rel-$plat
    zip -rq $rel-$plat.zip $rel-$plat
    rm -rf $rel-$plat
else
    echo no download for $plat
fi

# Download source and repackage
# Requires a valid $tagname, note the untarred directory is pypy-pypy-<hash>
# so make sure there is not another one
if wget https://bitbucket.org/pypy/pypy/get/$tagname.tar.bz2
then
    tar -xf $tagname.tar.bz2
    rm $tagname.tar.bz2
    mv pypy-pypy-* $rel-src
    tar --owner=root --group=root --numeric-owner -cjf $rel-src.tar.bz2 $rel-src
    zip -rq $rel-src.zip $rel-src
    rm -rf $rel-src
else
    echo source tarfile for $tagname not found on bitbucket, did you push the tag commit?
fi
# Print out the md5, sha1, sha256
#md5sum *.bz2 *.zip
#sha1sum *.bz2 *.zip
sha256sum *.bz2 *.zip

# Now upload all the bz2 and zip


