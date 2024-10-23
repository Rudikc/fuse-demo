import os
import json
import fuse
from fuse import FUSE, Operations
import errno

class JSONFS(Operations):
    def __init__(self, json_file):
        # Завантажуємо JSON-файл як словник
        self.json_file = json_file
        with open(json_file, 'r') as f:
            self.data = json.load(f)

    def getattr(self, path, fh=None):
        # Повертаємо інформацію про файл або каталог
        keys = self._get_path_keys(path)
        if keys is None:
            raise fuse.FuseOSError(errno.ENOENT)

        if isinstance(keys, dict):
            return dict(st_mode=(os.stat.S_IFDIR | 0o755), st_nlink=2)
        else:
            return dict(st_mode=(os.stat.S_IFREG | 0o644), st_size=len(str(keys)))

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

    def write(self, path, data, offset, fh):
        # Записуємо дані у файл (оновлюємо JSON)
        keys = self._get_path_keys(path, create_if_missing=True)
        if isinstance(keys, dict):
            raise fuse.FuseOSError(errno.EISDIR)

        # Оновлюємо значення в JSON
        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys)
        parent[final_key] = data.decode('utf-8').strip()

        # Зберігаємо зміни в JSON-файлі
        self._save_json()
        return len(data)

    def create(self, path, mode):
        # Створюємо новий файл в JSON
        parent_keys, final_key = self._get_parent_keys(path)
        parent = self._get_path_keys(parent_keys, create_if_missing=True)

        if final_key in parent:
            raise fuse.FuseOSError(errno.EEXIST)

        # Додаємо новий ключ з пустим значенням
        parent[final_key] = ""

        # Зберігаємо зміни
        self._save_json()
        return 0

    def _get_path_keys(self, path, create_if_missing=False):
        # Отримуємо ключі для шляху
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
        # Повертає шлях до батьківського каталогу та кінцевий ключ
        parts = path.strip('/').split('/')
        parent_keys = '/' + '/'.join(parts[:-1])
        final_key = parts[-1]
        return parent_keys, final_key

    def _save_json(self):
        # Зберігаємо зміни в JSON-файлі
        with open(self.json_file, 'w') as f:
            json.dump(self.data, f, indent=4)

if __name__ == '__main__':
    json_file = 'data.json'
    mount_point = './mnt'
    FUSE(JSONFS(json_file), mount_point, foreground=True)
