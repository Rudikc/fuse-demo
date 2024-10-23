import os
import json
import stat

import fuse
import errno
from fuse import FUSE, Operations

class JSONFS(Operations):
    def __init__(self, json_file):
        # Завантажуємо JSON-файл як словник
        with open(json_file, 'r') as f:
            self.data = json.load(f)

    def getattr(self, path, fh=None):
        # Повертаємо інформацію про файл або каталог
        keys = self._get_path_keys(path)
        if keys is None:
            raise fuse.FuseOSError(errno.ENOENT)

        if isinstance(keys, dict):
            return dict(st_mode=(stat.S_IFDIR | 0o755), st_nlink=2)
        else:
            return dict(st_mode=(stat.S_IFREG | 0o644), st_size=len(str(keys)))

    def readdir(self, path, fh):
        # Читаємо вміст каталогу
        keys = self._get_path_keys(path)
        if isinstance(keys, dict):
            return ['.', '..'] + list(keys.keys())
        raise fuse.FuseOSError(errno.ENOTDIR)

    def read(self, path, size, offset, fh):
        # Читаємо вміст файлу
        keys = self._get_path_keys(path)
        if isinstance(keys, dict):
            raise fuse.FuseOSError(errno.EISDIR)
        return str(keys).encode('utf-8')[offset:offset + size]

    def _get_path_keys(self, path):
        # Отримуємо ключі для шляху
        keys = self.data
        if path == '/':
            return keys
        for part in path.strip('/').split('/'):
            if isinstance(keys, dict) and part in keys:
                keys = keys[part]
            else:
                return None
        return keys

if __name__ == '__main__':
    json_file = 'data.json'
    mount_point = './mnt'
    FUSE(JSONFS(json_file), mount_point, foreground=True)
