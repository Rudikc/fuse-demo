import os
import json
import errno
from fuse import FUSE, FuseOSError, Operations

class JSONFS(Operations):
    def __init__(self, json_file):
        self.json_file = json_file
        with open(json_file, 'r') as f:
            self.data = json.load(f)
        self.fd = 0  # Файловий дескриптор

    def getattr(self, path, fh=None):
        keys = self._get_path_keys(path)
        if keys is None:
            raise FuseOSError(errno.ENOENT)

        uid, gid = os.getuid(), os.getgid()

        if isinstance(keys, dict):
            return {
                'st_mode': (0o40777),  # Каталог з повними правами
                'st_nlink': 2,
                'st_uid': uid,
                'st_gid': gid
            }
        else:
            return {
                'st_mode': (0o100666),  # Файл з правами читання та запису
                'st_nlink': 1,
                'st_size': len(str(keys)),
                'st_uid': uid,
                'st_gid': gid
            }

    def readdir(self, path, fh):
        keys = self._get_path_keys(path)
        if isinstance(keys, dict):
            return ['.', '..'] + list(keys.keys())
        raise FuseOSError(errno.ENOTDIR)

    def read(self, path, size, offset, fh):
        keys = self._get_path_keys(path)
        if isinstance(keys, dict):
            raise FuseOSError(errno.EISDIR)
        data = str(keys).encode('utf-8')
        return data[offset:offset + size]

    def open(self, path, flags):
        # Дозволяємо відкриття файлу для читання та запису
        self.fd += 1
        return self.fd

    def create(self, path, mode, fi=None):
        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys, create_if_missing=True)

        if final_key in parent:
            raise FuseOSError(errno.EEXIST)

        # Додаємо новий ключ з пустим значенням
        parent[final_key] = ""

        # Зберігаємо зміни
        self._save_json()

        self.fd += 1
        return self.fd

    def write(self, path, data, offset, fh):
        keys = self._get_path_keys(path, create_if_missing=True)
        if isinstance(keys, dict):
            raise FuseOSError(errno.EISDIR)

        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys)

        # Записуємо дані (як рядок)
        value = data.decode('utf-8')

        if offset == 0:
            parent[final_key] = value
        else:
            parent[final_key] += value

        # Зберігаємо зміни
        self._save_json()
        return len(data)

    def truncate(self, path, length, fh=None):
        keys = self._get_path_keys(path, create_if_missing=True)
        if isinstance(keys, dict):
            raise FuseOSError(errno.EISDIR)

        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys)
        parent[final_key] = parent[final_key][:length]

        # Зберігаємо зміни
        self._save_json()

    def unlink(self, path):
        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys)
        if final_key in parent:
            del parent[final_key]
            self._save_json()
        else:
            raise FuseOSError(errno.ENOENT)

    def mkdir(self, path, mode):
        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys, create_if_missing=True)

        if final_key in parent:
            raise FuseOSError(errno.EEXIST)

        # Додаємо новий порожній словник
        parent[final_key] = {}

        # Зберігаємо зміни
        self._save_json()

    def rmdir(self, path):
        self.unlink(path)

    def _get_path_keys(self, path, create_if_missing=False):
        keys = self.data
        if path == '/':
            return keys
        for part in path.strip('/').split('/'):
            if isinstance(keys, dict) and part in keys:
                keys = keys[part]
            elif create_if_missing and isinstance(keys, dict):
                keys[part] = {}
                keys = keys[part]
            else:
                return None
        return keys

    def _get_parent_keys(self, path):
        parts = path.strip('/').split('/')
        parent_keys = '/' + '/'.join(parts[:-1])
        final_key = parts[-1]
        return parent_keys, final_key

    def _save_json(self):
        with open(self.json_file, 'w') as f:
            json.dump(self.data, f, indent=4)

if __name__ == '__main__':
    json_file = 'data.json'
    mount_point = './mnt'
    FUSE(JSONFS(json_file), mount_point, foreground=True, allow_other=True)
