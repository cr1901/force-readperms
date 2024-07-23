# `force-readperms.py`

Forcefully add read permissions to a filesystem tree with multiple owners
using POSIX ACLs (requires `sudo`).

## Purpose/Use Case

`force-readperms` is a Python script which iterates over a directory tree,
finds which files are not readable by the current user, and adds a Named User
[Access Control List](https://www.usenix.org/legacy/publications/library/proceedings/usenix03/tech/freenix03/full_papers/gruenbacher/gruenbacher_html/main.html) entry using `setfacl` as appropriate.

My use case is that I do a hybrid of [`rsync`](https://rsync.samba.org/) and
[`borg`](https://www.borgbackup.org/) backups. `sudo rsync -a...` works fine
for preserving permissions when copying a file tree from one host to another.
However, it is generally a [bad idea](https://github.com/borgbackup/borg/issues/3587#issuecomment-362870308)
to run borg as more than one user. This means that if you have a file tree with
files owner by multiple users, permissions of files/dirs you don't own<sup>1</sup>
may prevent `borg` from being able to back up all of the files in-tree.

If you don't want to back up all files in a tree, the permissions mismatch may
not be a problem. However, I want to back up all files and prune them later,
and want to modify the tree as little as possible just to read it. In principle,
POSIX ACLs allow me to keep the original owner, group, and permissions<sup>2</sup>
of the file intact, while allowing me a carveout long enough just to copy the files
when `sudo` isn't available.

## Usage

The script is invoked as: `force_readperms.py [dir_root] [username]`.<sup>3</sup>

For any file that this script can't access in the given tree, this script sets
the read bit on files you own, or shells out to `sudo` to run `setfacl` to add
an ACL entry that gives you permission to read (_and only read_) files that you
don't own.

At this writing (2024-07-23), the `setfacl` invocations also modifies group
permissions due to how ACLs repurpose the group permissions as a mask (`setfacl -m`)
(maximum permissions possible for any named user/named group/owning group).
Therefore, right now, this script assumes that you don't really use ACLs much,
and that you're not going to restore the tree to a running system.
_The original group permissions are preserved as an additional ACL entry._

If there is desire for a reversal script and/or print out affected group
permissions, I may add this functionality.

I hope I never have to use this script again, but I wrote it, it works for my
use case, it seems pretty robust. So I'm releasing it as a courtesy. Use this
script at your own risk. _I absolve myself of any responsibility if you run
this script on a live system and hose it._

## License

Copyright 2024 William D. Jones

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


## Footnotes

1. Or even files you _do_ own, if the read bit of the owner is cleared!
2. Currently, group permissions are altered due to ACL mask calculation, but
   _the original group permissions are preserved as a separate owning group
   ACL entry._
3. The `username` and `dir_root` order is subject to change if I have a pressing need
   to be able to pass multiple `dir_root`s at once.
