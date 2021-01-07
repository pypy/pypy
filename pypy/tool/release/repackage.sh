#! /bin/bash

# Edit these appropriately before running this script
pmaj=3  # python main version: 2 or 3
pmin=6  # python minor version
maj=7
min=3
rev=3
#rc=rc2  # set to blank for actual release

function maybe_exit {
    if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
        # script is being run, not "sourced" (as in "source repackage.sh")
        # so exit
        exit 1
    fi
}

case $pmaj in
    "2") exe=pypy;;
    "3") exe=pypy3;;
    *) echo invalid pmaj=$pmaj; maybe_exit
esac

branchname=release-pypy$pmaj.$pmin-v$maj.x # ==OR== release-v$maj.x  # ==OR== release-v$maj.$min.x
# tagname=release-pypy$pmaj.$pmin-v$maj.$min.$rev  # ==OR== release-$maj.$min
tagname=release-pypy$pmaj.$pmin-v$maj.$min.${rev}$rc  # ==OR== release-$maj.$min

echo checking hg log -r $branchname
hg log -r $branchname || maybe_exit
echo checking hg log -r $tagname
hg log -r $tagname || maybe_exit
hgrev=`hg id -r $tagname -i`

rel=pypy$pmaj.$pmin-v$maj.$min.${rev}$rc

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # script is being run, not "sourced" (as in "source repackage.sh")

    # The script should be run in an empty in the pypy tree, i.e. pypy/tmp
    if [ "`ls . | wc -l`" != "0" ]
    then
        echo this script must be run in an empty directory
        exit 1
    fi
fi

function repackage_builds {
    # Download latest builds from the buildmaster, rename the top
    # level directory, and repackage ready to be uploaded 
    actual_ver=xxxxxxxxxxxxxxx
    for plat in linux linux64 osx64 aarch64 s390x # linux-armhf-raspbian linux-armel
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
}

function repackage_source {
    # Requires a valid $tagname
    hg archive -r $tagname $rel-src.tar.bz2
    hg archive -r $tagname $rel-src.zip
}

function print_sha256 {
    # Print out the md5, sha1, sha256
    #md5sum *.bz2 *.zip
    #sha1sum *.bz2 *.zip
    sha256sum *.bz2 *.zip
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # script is being run, not "sourced" (as in "source repackage.sh")
    # so run the functions
    repackage_builds
    repackage_source
    print_sha256
fi
# Now upload all the bz2 and zip
