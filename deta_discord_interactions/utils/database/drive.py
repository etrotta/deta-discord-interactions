import os
import typing
from typing import Literal, Optional, Union

from deta import _Drive as DetaDrive, Drive as get_drive
from deta_discord_interactions.utils.database._local_drive import Drive as LocalDrive
from deta_discord_interactions.utils.database.exceptions import DriveOutOfBoundsError

class DrivePath:
    def __init__(self, path: str, *, drive: Union[DetaDrive, LocalDrive, None] = None):
        assert '//' not in path, "Paths cannot contain `//`"
        assert '..' not in path, "Paths cannot contain `..`"
        assert './' not in path, "Paths cannot contain `./`"
        assert './' not in path, "Paths cannot contain `_DIR_`"
        self._path = path
        self._drive = drive

    def check_valid_dir(self) -> bool:
        return (
            self._drive is not None
            and self._path.startswith('/')
            and self._path.endswith('/')
        )

    def check_valid_file(self) -> bool:
        return (
            self._drive is not None
            and self._path.startswith('/')
            and not self._path.endswith('/')
            and len(self._path.strip('/')) >= 1
        )

    def __hash__(self) -> int:
        return hash(self._path)

    # Just so that you can sort paths for displaying
    def __gt__(self, other):  
        if not isinstance(other, DrivePath):
            return NotImplemented
        return self._path > other._path

    def __lt__(self, other):
        if not isinstance(other, DrivePath):
            return NotImplemented
        return self._path < other._path

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return other == self._path
        return isinstance(other, type(self)) and self._path == other._path

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._path})"

    def joinpath(self, *components: str) -> 'DrivePath':
        result = self._path
        for part in components:
            if part == '..':
                if result == '/':
                    raise DriveOutOfBoundsError(f"Relative path {components} out of bounds for path {self}")
                result = result.rstrip('/').rsplit('/', 1)[0] + '/'
            else:
                result = result + '/' + part
        return DrivePath(result.replace('//', '/'), drive=self._drive)

    def relative_to(self, other: Union[str, 'DrivePath']) -> 'DrivePath':
        if isinstance(other, DrivePath):
            comp = other._path
        else:
            comp = other
        if not self._path.startswith(comp):
            raise ValueError(f"Path {self} does not starts with {other}")
        return DrivePath(self._path.removeprefix(comp).lstrip('/'), drive=self._drive)

    def is_relative_to(self, other: Union[str, 'DrivePath']) -> bool:
        if isinstance(other, DrivePath):
            comp = other._path
        else:
            comp = other
        return self._path.startswith(comp)

    def __truediv__(self, other: Union[str, 'DrivePath']) -> 'DrivePath':  # self / other
        if isinstance(other, DrivePath):
            other = other._path
        parts = other.split('/')
        return self.joinpath(*parts)

    def __rtruediv__(self, other: Union[str, 'DrivePath']) -> 'DrivePath':  # other / self
        if isinstance(other, str):
            other = DrivePath(other, drive=self._drive)
        parts = self._path.split('/')
        return other.joinpath(*parts)

    @property
    def deta_path(self) -> str:
        "Deta Drives does not actually seems to support subfolders, so replace it like this"
        return self._path.replace('/', "_DIR_").removeprefix("_DIR_")

    @classmethod
    def from_deta_path(cls, path: str, *, drive: Union[DetaDrive, LocalDrive, None] = None) -> 'DrivePath':
        return DrivePath('/' + path.replace('_DIR_', '/').removeprefix('/'), drive=drive)

    @property
    def name(self) -> str:
        "The final path component, including its suffixes"
        return self._path.rstrip('/').rsplit('/', 1)[-1]

    @property
    def stem(self) -> str:
        "The final path component, minus its last suffix."
        name = self.name
        idx = name.rfind('.')
        if idx != -1:
            return name[:idx]
        return name

    @property
    def suffix(self) -> str:
        "The final component's last suffix, if any."
        name = self.name
        idx = name.rfind('.')
        if idx != -1:
            return name[idx:]
        return ''

    @property
    def suffixes(self) -> list[str]:
        """The final component's suffixes, if any.
        
        These include the leading periods. For example: ['.tar', '.gz']"""
        return [f'.{sfx}' for sfx in self.name.split('.')[1:]]

    @property
    def parent(self) -> 'DrivePath':
        return DrivePath(self._path.rstrip('/').rsplit('/', 1)[0] + '/', drive=self._drive)

    @property
    def parts(self) -> list[str]:
        return [part for part in self._path.split('/')]

    def exists():
        "There does not exists a really good way to implement this using the Deta API."
        raise NotImplementedError()

    def is_dir(self) -> bool:
        "Checks if this would represent a valid directory. Does NOT checks if it exists"
        return self._path.startswith('/') and self._path.endswith('/')

    def is_file(self) -> bool:
        "Checks if this would represent a valid file. Does NOT checks if it exists"
        return self._path.startswith('/') and not self._path.endswith('/')

    def match(self, pattern: str) -> bool:  # TODO if I feel like it (should be doable)
        raise NotImplementedError()

    def with_name(self, name: str) -> 'DrivePath':
        "Returns a new path replacing the name component of this with the given parameter"
        root = self._path.rsplit('/', 1)[0]
        return DrivePath(root + '/' + name, drive=self._drive)

    def with_stem(self, stem: str) -> 'DrivePath':
        "Returns a new path replacing the stem component of this with the given parameter"
        return self.with_name(stem + self.suffix)

    def with_suffix(self, suffix: str) -> 'DrivePath':
        "Returns a new path replacing the suffix component of this with the given parameter. Must include the '.' in the suffix."
        if not suffix.startswith('.'):
            raise Exception("The new suffix must start with `.`")
        if suffix == '.':
            raise Exception("The suffix cannot be `.` on it's own")
        base = self.name[:-len(self.suffix) or None]
        return self.with_name(base + '.' + suffix)

    def iterdir(self) -> list['DrivePath']:
        "Returns all files "
        if not self.check_valid_dir:
            raise Exception("This method can only be called on absolute paths refering to directories")
        files: list[str] = []
        last = ''
        parent = self.deta_path
        while last is not None:
            files_data = self._drive.list(limit=1000, prefix=parent, last=last)
            last = files_data.get("paging", {}).get("last")
            files.extend(files_data.get("names"))
        return [DrivePath.from_deta_path(file, drive=self._drive) for file in files if file != parent]

    # TODO IMPLEMENT SOMEDAY
    def glob(self, pattern: str) -> typing.NoReturn:
        "Use iterdir() and filter yourself for now or make a Pull Request"
        raise NotImplementedError()
    def rglob(self, pattern: str) -> typing.NoReturn:
        "Use iterdir() and filter yourself for now or make a Pull Request"
        raise NotImplementedError()

    def get(self) -> Optional[bytes]:
        "Returns the content under this path. If the file was not found, returns None"
        file = self._drive.get(self.deta_path)
        if file is None:
            return None
        return file.read()

    def put(self, data: Optional[bytes] = None, local_file: Optional[str] = None) -> None:
        "Sets the content under this path"
        if not ((data is None) ^ (local_file is None)):
            raise Exception("You must specify exactly one of `data` or `local_file`.")
        self._drive.put(self.deta_path, data=data, path=local_file)

    def open(self, mode: Literal['r', 'w', 'rb', 'wb'], encoding: Optional[str] = None) -> 'ProxyFile':
        if mode not in {'r', 'w', 'rb', 'wb'}:
            raise Exception(f"Mode {mode} not supported for Drive Paths")
        if mode.endswith('b') and encoding is not None:
            raise Exception("You cannot specify an `encoding` when using a binary mode")
        return ProxyFile(path=self, mode=mode, encoding=encoding)

    def touch():  # would have to get() to do it (put() overwrites if it exists)
        raise NotImplementedError()

    def unlink(self):
        self._drive.delete(self.deta_path)
    def delete(self):
        "Alias for unlink"
        self.unlink()
    def remove(self):
        "Alias for unlink"
        self.unlink()

    def rename(self):
        raise NotImplementedError()

    def replace(self):
        raise NotImplementedError()

    def read_bytes(self) -> bytes:
        "Reads as text. If the file was not found, returns an empty byte string."
        return self.get() or b''

    def read_text(self, encoding: str = 'UTF-8') -> str:
        "Reads as text. If the file was not found, returns an empty string."
        return (self.get() or b'').decode(encoding)

    def write_bytes(self, data: bytes):
        self.put(data)
    
    def write_text(self, data: str, encoding: str = 'UTF-8'):
        self.put(data.encode(encoding))


class ProxyFile:
    def __init__(self, path: DrivePath, mode: Literal['r', 'w', 'rb', 'wb'], encoding: Optional[str] = None):
        self._path: DrivePath = path
        self._open: bool = False
        self._content: Union[str, bytes, None]
        if mode == 'w':
            self._content = ''
        elif mode == 'wb':
            self._content = b''
        else:
            self._content = None
        self._cursor: int = 0
        self._mode = mode
        self.encoding = encoding or 'UTF-8'

    def __enter__(self):
        self._open = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._open = False
        if exc_val is not None:
            print("Aborting file write due to error")
            return
        if self._mode == 'w':
            self._path.put(self._content.encode(self.encoding))
        elif self._mode == 'wb':
            self._path.put(self._content)

    def _load_content(self):
        if self._content is None:
            content = self._path.get()
            if self._mode == 'r':
                content = content.decode(self.encoding)
            self._content = content

    def read(self) -> Union[str, bytes]:
        assert self._open, "Can only Read from Drive files inside of a context manager."
        assert self._mode in {'r', 'rb'}, "Can only read when using a Read mode"
        self._load_content()
        result = self._content[self._cursor:]
        self._cursor += len(result)
        return result

    def readline(self) -> str:
        assert self._open, "Can only Read from Drive files inside of a context manager."
        assert self._mode == 'r', "Can only readline when using `r` mode"
        self._load_content()
        idx = self._content.find('\n', self._cursor + 1)
        if idx == -1:
            idx = None
        else:
            idx += 1
        result = self._content[self._cursor:idx]
        self._cursor += len(result)
        return result

    def readlines(self) -> Union[list[str], list[bytes]]:
        out = []
        while True:
            line = self.readline()
            if not line: return out
            out.append(line)

    def write(self, data: Union[str, bytes]):
        assert self._open, "Can only Write to Drive files inside of a context manager."
        assert self._mode in {'w', 'wb'}, "Can only write when using a Write mode."
        self._content += data
        self._cursor += len(data)  # Not that it matters


class Drive(DrivePath):
    def __init__(self, name: str, *, drive_mode: Optional[str] = None, drive_folder: Optional[str] = None):
        """Deta Drive wrapper

        Parameters
        ----------
        name : str
            Which name to use for the Deta Base
        drive_mode: Optional[str], support values: "DETA", "MEMORY", "DISK"
            Which mode to use for the drive.
            DETA: Uses Deta Drive
            DISK: Saves the data to a local file instead of using Deta Drive.
            MEMORY: Keep the data in memory but do not save at all.
            By default, uses the `DETA_ORM_DATABASE_MODE` environment variable, or "DETA" if unset
        drive_folder : str
            If using `drive_mode = "DISK"`, you can use this to specify where the files should be stored.
            If missing, expects for the `DETA_ORM_FOLDER` environment variable to be set.
        """
        if drive_mode is None:
            drive_mode = os.getenv("DETA_ORM_DATABASE_MODE", "DETA")
        if drive_mode.startswith("DETA"):
            drive = get_drive(name)
        elif drive_mode == "MEMORY":
            drive = LocalDrive(name, sync_disk=False)
        elif drive_mode == "DISK":
            drive = LocalDrive(name, sync_disk=True, folder=drive_folder)
        else:
            raise Exception("Invalid value for DETA_ORM_DATABASE_MODE")

        super().__init__('/', drive=drive)
