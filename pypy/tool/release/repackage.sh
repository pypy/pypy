# Edit these appropriately before running this script
maj=2
min=6
rev=0
# This script will download latest builds from the buildmaster, rename the top
# level directory, and repackage ready to be uploaded to bitbucket. It will also
# download source, assuming a tag for the release already exists, and repackage them.

for plat in linux linux64 linux-armhf-raspbian linux-armhf-raring linux-armel osx64
  do
    wget http://buildbot.pypy.org/nightly/release-$maj.$min.x/pypy-c-jit-latest-$plat.tar.bz2
    tar -xf pypy-c-jit-latest-$plat.tar.bz2
    rm pypy-c-jit-latest-$plat.tar.bz2
    mv pypy-c-jit-*-$plat pypy-$maj.$min.$rev-$plat
    tar --owner=root --group=root --numeric-owner -cvjf pypy-$maj.$min.$rev-$plat.tar.bz2 pypy-$maj.$min.$rev-$plat
    rm -rf pypy-$maj.$min.$rev-$plat
  done

plat=win32
wget http://buildbot.pypy.org/nightly/release-$maj.$min.x/pypy-c-jit-latest-$plat.zip
unzip pypy-c-jit-latest-$plat.zip
mv pypy-c-jit-*-$plat pypy-$maj.$min.$rev-$plat
zip -r pypy-$maj.$min.$rev-$plat.zip pypy-$maj.$min.$rev-$plat
rm -rf pypy-$maj.$min.$rev-$plat

# Do this after creating a tag, note the untarred directory is pypy-pypy-<hash>
# so make sure there is not another one
wget https://bitbucket.org/pypy/pypy/get/release-$maj.$min.$rev.tar.bz2
tar -xf release-$maj.$min.$rev.tar.bz2
mv pypy-pypy-* pypy-$maj.$min.$rev-src
tar --owner=root --group=root --numeric-owner -cvjf pypy-$maj.$min.$rev-src.tar.bz2 pypy-$maj.$min.$rev-src
zip -r pypy-$maj.$min.$rev-src.zip pypy-$maj.$min.$rev-src
rm -rf pypy-$maj.$min.$rev-src

# Print out the md5, sha1
md5sum *.bz2 *.zip
sha1sum *.bz2 *.zip

# Now upload all the bz2 and zip


