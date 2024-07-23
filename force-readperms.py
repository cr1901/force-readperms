#!/usr/bin/env python3

import logging
import os
import stat
import sys
import argparse
import subprocess
import pathlib

from pwd import getpwnam

logger = logging.getLogger("force-readperms")


def walk_and_examine_dirs(dir_root, username, err_list):
    username_uid = getpwnam(username).pw_uid
    def collect_errors(f):
        fn = pathlib.Path(f.filename)

        if isinstance(f, NotADirectoryError):
            assert False, "Single-file support not yet implemented"

        # Figure out whether the directory itself doesn't have read
        # permissions, or the parent doesn't have execute permissions.
        try:
            dirinfo = os.stat(fn)
            owner = dirinfo.st_uid
            mode = dirinfo.st_mode
        except PermissionError:
            logger.debug(f" Do not have permissions to read parent directory {str(fn.parent)}")
            err_list.append(str(fn.parent))
        else:
            if owner == username_uid and ((mode & 0o400) == 0):
                # In POSIX ACLs, owner perms override named user perms.
                logger.info(f" {username} owns {str(fn)}, adding read perms via os.chmod")
                os.chmod(fn, dirinfo.st_mode | 0o400, follow_symlinks=False)
            else:
                err_list.append(str(fn))

    for _ in os.walk(dir_root, onerror=collect_errors):
        pass


def walk_dirs_and_examine_files(dir_root, username, err_list):
    username_uid = getpwnam(username).pw_uid

    for root, _, files in os.walk(dir_root):
        dirn = pathlib.Path(root)
        for f in files:
            # Figure out whether the file itself doesn't have read
            # permissions, or the parent directory doesn't have execute
            # permissions.
            try:
                fileinfo = os.stat(dirn / f, follow_symlinks=False)
                owner = fileinfo.st_uid
                mode = fileinfo.st_mode

                if owner == username_uid and ((mode & 0o400) == 0):
                    # In POSIX ACLs, owner perms override named user perms.
                    logger.info(f" {username} owns {str(dirn / f)}, adding read perms via os.chmod")
                    os.chmod(dirn / f, mode | 0o400, follow_symlinks=False)
                    continue

            except PermissionError:
                if str(dirn) not in err_list:
                    err_list.append(str(dirn))
                continue

            try:
                if stat.S_ISDIR(mode) or stat.S_ISREG(mode):
                    with open(dirn / f, "rb"):
                        pass
                elif stat.S_ISFIFO(mode):
                    logger.debug(" Opening FIFO {}".format(str(dirn / f)))
                    os.open(dirn / f, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                # TODO: ISCHR/ISBLK
            
            except PermissionError as e:
                err_list.append(str(dirn / f))


def setacl_loop(collector, username, limit):
    err_list = []
    arg_buf = []
    loop_count = 0

    collector(username, err_list)

    loop_count = 0
    while err_list and loop_count < limit:
        base_cmd = ["sudo", "setfacl", "-m", f"user:{username}:rX"]
        arg_buf = []
        count = 0
        for f in err_list:
            count += len(f)
            if count > 4096:
                base_cmd.extend(arg_buf)
                logger.info(" Running {}".format(" ".join(base_cmd)))
                subprocess.run(base_cmd)

                base_cmd = ["sudo", "setfacl", "-m", f"user:{username}:rX"]
                arg_buf = []
                count = 0
            else:
                arg_buf.append(f)

        if arg_buf:
            base_cmd.extend(arg_buf)
            logger.info(" Running {}".format(" ".join(base_cmd)))
            subprocess.run(base_cmd)

        err_list.clear()
        collector(username, err_list)

        loop_count += 1


def main(dir_root, username, limit, verbose):
    username_uid = getpwnam(username).pw_uid
    if verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    logging.basicConfig(level=loglevel)

    logger.debug(" Finding directories which need read permissions forced")
    setacl_loop(lambda u, e: walk_and_examine_dirs(dir_root, u, e), username, limit)  

    # if single_file:
    #     cmd = ["sudo", "setfacl", "-m", f"user:{username}:rX", single_file]
    #     logger.info(" Running {}".format(" ".join(cmd)))
    #     subprocess.run(cmd)
    #     sys.exit(0)

    logger.debug(" Finding files which need read permissions forced")
    setacl_loop(lambda u, e: walk_dirs_and_examine_files(dir_root, u, e), username, limit)        


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Force read permissions of a file tree using read ACLs")
    parser.add_argument("dir_root")
    parser.add_argument("username")
    parser.add_argument("-v", action="store_true", help="verbose mode")
    parser.add_argument("-l", default=50, help="iteration limit")
    args = parser.parse_args()

    main(args.dir_root, args.username, args.l, args.v)

