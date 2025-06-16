/bin/rm test.ogg
ffmpeg -f lavfi -i "anullsrc=duration=0.0001" -c:a libvorbis -q:a 0 test.ogg
md5sum test.ogg
dd if=/dev/zero bs=1 count=2 >> test.ogg
