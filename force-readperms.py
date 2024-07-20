#!/usr/bin/env python3

import logging
import os
import stat
import argparse
import subprocess
import pathlib

logger = logging.getLogger("force-readperms")


def main(dir_root, username, limit, verbose):
    if verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO

    logging.basicConfig(level=loglevel)

    err_list = []
    def collect_errors(f):
        fn = pathlib.Path(f.filename)

        # Figure out whether the directory itself doesn't have read
        # permissions, or the parent doesn't have execute permissions.
        try:
            os.stat(fn)
        except PermissionError:
            err_list.append(str(fn.parent))
        else:
            err_list.append(str(fn))

    for _ in os.walk(dir_root, onerror=collect_errors):
        pass

    arg_buf = []
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
        for _ in os.walk(dir_root, onerror=collect_errors):
            pass

        loop_count += 1

    assert len(err_list) == 0

    for root, _, files in os.walk(dir_root):
        dirn = pathlib.Path(root)
        for f in files:
            # Figure out whether the directory itself doesn't have read
            # permissions, or the parent doesn't have execute permissions.
            try:
                mode = os.stat(dirn / f, follow_symlinks=False).st_mode
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

                # TODO: Edge case: "setfacl -m u::rX foo" (chmod +r foo?) may
                # be necessary if we are the owner of the file, and the file
                # doesn't have read perms for owner.
                #
                # In POSIX ACLs, owner perms override named user perms.
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
        for root, _, files in os.walk(dir_root):
            dirn = pathlib.Path(root)
            for f in files:
                # Figure out whether the directory itself doesn't have read
                # permissions, or the parent doesn't have execute permissions.
                try:
                    mode = os.stat(dirn / f, follow_symlinks=False).st_mode
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

        loop_count += 1   


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Force read permissions of a file tree using read ACLs")
    parser.add_argument("dir_root")
    parser.add_argument("username")
    parser.add_argument("-v", action="store_true", help="verbose mode")
    parser.add_argument("-l", default=50, help="iteration limit")
    args = parser.parse_args()

    main(args.dir_root, args.username, args.l, args.v)

