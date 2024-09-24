#! /bin/bash

set -e

# Edit these appropriately before running this script
pmaj=3  # python main version: 2 or 3
pmin=10  # python minor version
maj=7
min=3
rev=17
#rc=rc2  # comment this line for actual release

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

echo checking git rev-parse  $branchname
git rev-parse --short=12 $branchname
echo checking git rev-parse $tagname^{}
githash=$(git rev-parse --short=12 $tagname^{})
echo $githash

rel=pypy$pmaj.$pmin-v$maj.$min.${rev}$rc

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # script is being run, not "sourced" (as in "source repackage.sh")

    # The script should be run in an empty in the pypy tree, i.e. pypy/tmp
    if [  -n "$(ls .)"  ]
    then
        echo this script must be run in an empty directory
        exit 1
    fi
fi

if [ "$rc" == "" ]
then
    wanted="\"$maj.$min.$rev${rc/rc/-candidate}\""
else
    wanted="\"$maj.$min.$rev\""
fi

function repackage_builds {
    # Download latest builds from the buildmaster, rename the top
    # level directory, and repackage ready to be uploaded 
    for plat in linux linux64 macos_x86_64 macos_arm64 aarch64
      do
        echo downloading package for $plat
        if wget -q --show-progress http://buildbot.pypy.org/nightly/$branchname/pypy-c-jit-latest-$plat.tar.bz2
        then
            echo $plat downloaded 
        else
            echo $plat no download available
            continue
        fi
        gitcheck=`tar -tf pypy-c-jit-latest-$plat.tar.bz2 |head -n1 | cut -d- -f5`
        if [ "$gitcheck" != "$githash" ]
        then
            echo xxxxxxxxxxxxxxxxxxxxxx
            echo $plat git short hash mismatch, expected $githash, got $gitcheck
            echo xxxxxxxxxxxxxxxxxxxxxx
            rm pypy-c-jit-latest-$plat.tar.bz2
            continue
        fi
        tar -xf pypy-c-jit-latest-$plat.tar.bz2
        rm pypy-c-jit-latest-$plat.tar.bz2

        # Check that this is the correct version
        if [ "$pmin" == "7" ] # python2.7, 3.7
        then
            actual_ver=$(grep PYPY_VERSION pypy-c-jit-*-$plat/include/patchlevel.h |cut -f3 -d' ')
        else
            actual_ver=$(grep PYPY_VERSION pypy-c-jit-*-$plat/include/pypy$pmaj.$pmin/patchlevel.h |cut -f3 -d' ')
        fi
        if [ $actual_ver != $wanted ]
        then
            echo xxxxxxxxxxxxxxxxxxxxxx
            echo version mismatch, expected $wanted, got $actual_ver for $plat
            echo xxxxxxxxxxxxxxxxxxxxxx
            exit -1
            rm -rf pypy-c-jit-*-$plat
            continue
        fi

        # Move the files into the correct directory and create the tarball
        plat_final=$plat
        if [ $plat = linux ]; then
            plat_final=linux32
        fi
        mv pypy-c-jit-*-$plat $rel-$plat_final
        echo packaging $plat_final
        if [[ "$OSTYPE" == darwin* ]]; then
            # install gtar with brew install gnu-tar
            gtar --owner=root --group=root --numeric-owner -cjf $rel-$plat_final.tar.bz2 $rel-$plat_final
        else
            tar --owner=root --group=root --numeric-owner -cjf $rel-$plat_final.tar.bz2 $rel-$plat_final
        fi
        rm -rf $rel-$plat_final
      done
    # end of "for" loop
    for plat in win64 # win32
      do
        if wget -q --show-progress http://buildbot.pypy.org/nightly/$branchname/pypy-c-jit-latest-$plat.zip
        then
            echo $plat downloaded 
        else
            echo $plat no download available
            continue
        fi
        unzip -q pypy-c-jit-latest-$plat.zip
        rm pypy-c-jit-latest-$plat.zip
        actual_ver=$(grep PYPY_VERSION pypy-c-jit-*-$plat/include/patchlevel.h |cut -f3 -d' ')
        if [ $actual_ver != $wanted ]
        then
            echo xxxxxxxxxxxxxxxxxxxxxx
            echo version mismatch, expected $wanted, got $actual_ver for $plat
            echo xxxxxxxxxxxxxxxxxxxxxx
            rm -rf pypy-c-jit-*-$plat
            continue
        fi
        mv pypy-c-jit-*-$plat $rel-$plat
        zip -rq $rel-$plat.zip $rel-$plat
        rm -rf $rel-$plat
      done
    # end of "for" loop
}

function repackage_source {
    # Requires a valid $tagname
    cwd=${PWD}
    if [ "$pmaj" == "2" ]; then
        branch=main;
    else
        branch=py$pmaj.$pmin
    fi
    echo "node: $githash" > ../.hg_archival.txt
    echo "branch: $branchname" >> ../.hg_archival.txt
    echo "tag: $tagname" >> ../.hg_archival.txt
    git config tar.tar.bz2.command "bzip2 -c"
    $(cd ..; git archive --prefix $rel-src/ --add-file=.hg_archival.txt --output=${cwd}/$rel-src.tar.bz2 $tagname)
    $(cd ..; git archive --prefix $rel-src/ --add-file=.hg_archival.txt --output=${cwd}/$rel-src.zip $tagname)
}

function print_sha256 {
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
echo don\'t forget to push the tags "git push --tags"
