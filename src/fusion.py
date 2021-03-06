from __future__ import with_statement

import os
import threading
import sys
import errno
from drive_facade import driveFacade
from file_methods import fileMethods
from fuse import FUSE, FuseOSError, Operations


class Passthrough(Operations):
    def __init__(self, root):
        self.root = root
        self.fm = fileMethods()

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _parent_path(self,path):
        parent = path[:-len(os.path.basename(path))-1]
        if parent == '':
            return '/'
        return parent


    def access(self, path, mode):
        full_path = self._full_path(path)
        parent_path = self._parent_path(path)
        print("access : ", path)
        self.fm.access_threaded(path,full_path,parent_path)
        self.fm.sync_threaded(path, full_path, parent_path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
        

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        parent_path = self._parent_path(path)
        dirents = ['.', '..']
        print("ls :", path)
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        print('rmdir :',path)
        full_path = self._full_path(path)
        parent_path = self._parent_path(path)
        self.fm.delete_threaded(path,parent_path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        print('mkdir :',path)
        parent_path = self._parent_path(path)
        self.fm.mkdir_threaded(path,parent_path)
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        print('unlink :',path)
        parent_path = self._parent_path(path)
        self.fm.delete_threaded(path,parent_path)
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        return os.symlink(name, self._full_path(target))

    def rename(self, old, new):
        print('rename :', old, new)
        old_vals = {
            'path' : old,
            'full_path' : self._full_path(old),
            'parent_path' : self._parent_path(old)
        }
        new_vals = {
            'path' : new,
            'full_path' : self._full_path(new),
            'parent_path' : self._parent_path(new)
        }
        self.fm.move_threaded(old_vals, new_vals)
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)


    def open(self, path, flags):
        print('open :',path)
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        print('create :',path)
        full_path = self._full_path(path)
        parent_path = self._parent_path(path)
        o = os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)
        self.fm.create_threaded(path,full_path,parent_path)
        return o

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        print('write :',path)
        full_path = self._full_path(path)
        parent_path = self._parent_path(path)
        self.fm.update_threaded(path, full_path, parent_path)
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)


def main(mountpoint):
    if not os.path.exists('src/root'):
        os.mkdir('src/root')
    FUSE(Passthrough('src/root'), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    main(sys.argv[1])