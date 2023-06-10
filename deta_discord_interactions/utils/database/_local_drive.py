import pathlib
import io
import os
from typing import Optional
import typing


class FileProxy: pass

class RealFileProxy(FileProxy):
    def __init__(self, path: str) -> None:
        self.path = path
    def read(self):
        with open(self.path, 'rb') as f:
            return f.read()

class MemoryProxy(FileProxy):
    def __init__(self, contents: bytes):
        self.contents = contents
    def read(self):
        return self.contents

class DiskDriveBackend:
    """Drive backend that saves to disk."""
    def __init__(self, drive_name: str, folder: Optional[pathlib.Path]):
        self.name = drive_name
        if folder:
            self._root = folder / drive_name
        elif (env_folder := os.getenv("DETA_ORM_FOLDER")):
            self._root = pathlib.Path(env_folder) / drive_name
        else:
            raise Exception("When using a Database on DISK mode, you must specify the path."\
                "\nUsing the `disk_base_path` keyword argument or the `DETA_ORM_FOLDER` environment variable.")
        self._root.mkdir(exist_ok=True, parents=True)

    def __contains__(self, name: str) -> bool:
        return (self._root / name).is_file()
    
    def get(self, name: str) -> Optional[RealFileProxy]:
        if (file := (self._root / name)).is_file():
            return RealFileProxy(file)
        return None
    
    def delete(self, name: str) -> bool:
        file = (self._root / name)
        if file.exists():
            file.unlink()
            return True
        return False
    
    def list(self) -> list[str]:
        return sorted(path.name for path in self._root.iterdir())

    def put(self, name: str, data: bytes):
        with (self._root / name).open('wb') as f:
            f.write(data)


class MemoryDriveBackend:
    """Drive backend that saves to memory."""
    def __init__(self, drive_name: str):
        self.name = drive_name
        self.files: dict[str, bytes] = {}

    def __contains__(self, name: str) -> bool:
        return name in self.files

    def get(self, name: str) -> Optional[MemoryProxy]:
        file = self.files.get(name)
        if file is not None:
            return MemoryProxy(file)
        return None

    def delete(self, name: str):
        del self.files[name]

    def list(self) -> list[str]:
        return sorted(self.files.keys())

    def put(self, name: str, data: bytes):
        self.files[name] = data

_memory_inventory: dict[str, MemoryDriveBackend] = {}

class Drive:
    def __init__(self, name: str, sync_disk: bool = False, folder: Optional[str] = None):
        self.name = name
        if sync_disk:
            self.inventory = DiskDriveBackend(name, pathlib.Path(folder) if folder else None)
        else:
            self.inventory = _memory_inventory.setdefault(name, MemoryDriveBackend(name))

    def get(self, name: str) -> Optional[FileProxy]:
        return self.inventory.get(name)

    def delete_many(self, names: list[str]):
        deleted, failure = [], []
        for name in names:
            if self.inventory.delete(name):
                deleted.append(name)
            else:
                failure.append(name)
        return {
            "deleted" : deleted,
            "failed": {
                file: "file (probably) does not exists"
                for file in failure
            }
        }

    def delete(self, name: str):
        if not self.inventory.delete(name):
            raise Exception(f"Failed to delete '{name}'")
        return name

    def list(self, limit: int = 1000, prefix: Optional[str] = None, last: Optional[str] = None):
        files = [
            file for file in self.inventory.list()
            if (prefix is None or file.startswith(prefix)) and (last is None or file > last)
        ]
        if len(files) > limit:
            files = files[:limit]
            last = files[-1]
        else:
            last = None
        return {
            "names": files,
            "paging": {
                "size": len(files),
                "last": last,
            }
        }

    def put(
        self,
        name: str,
        data: typing.Union[str, bytes, io.TextIOBase, io.BufferedIOBase, io.RawIOBase, None] = None,
        *,
        path: Optional[str] = None,
        content_type = None,
    ) -> str:
        assert name, "No name provided"
        assert path or data, "No data or path provided"
        assert not (path and data), "Both path and data provided"

        if data is None:
            data = open(path, 'rb')
        if hasattr(data, 'read'):
            data = data.read()
        if isinstance(data, str):
            data = data.encode('UTF-8')

        self.inventory.put(name, data)

        return name
