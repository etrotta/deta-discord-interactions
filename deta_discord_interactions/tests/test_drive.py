import pytest

from deta_discord_interactions.utils.database import Drive, DrivePath, ProxyFile
from deta_discord_interactions.utils.database._local_drive import DiskDriveBackend

@pytest.fixture()
def mem_drive():
    # NOTE: `MEMORY` USES A GLOBAL STATE TO SHARE INVENTORY BETWEEN DRIVES USING THE SAME NAME...
    return Drive("test_drive", drive_mode="MEMORY")

@pytest.fixture()
def disk_drive(tmp_path):
    return Drive("test_drive", drive_mode="DISK", drive_folder=tmp_path)

def test_properties():
    file = DrivePath("/folder/file.json")
    assert file.name == "file.json"
    assert file.stem == "file"
    assert file.suffix == ".json"
    file2 = DrivePath("/folder/file.tar.gz")
    assert file2.suffix == ".gz"
    assert file2.suffixes == [".tar", ".gz"]
    folder = DrivePath("/folder/")
    assert folder.name == "folder"
    assert folder.stem == "folder"
    assert folder.suffix == ""
    assert file.parent == folder
    assert file.relative_to(folder) == "file.json"
    assert file.is_file()
    assert folder.is_dir()
    assert not folder.is_file()
    assert not file.is_dir()


def test_join_path():
    root = DrivePath("/")
    a = root / 'a'
    assert a == '/a'
    b = a / 'b'
    assert b == '/a/b'
    c = b / 'c/'
    assert c == '/a/b/c/'
    d = c / 'd/'
    assert d == '/a/b/c/d/'
    e = d / 'e'
    assert e == '/a/b/c/d/e'
    assert e.parent == d
    assert (e / '..') == d
    assert (e / '../..') == c
    assert (e / '..' / '..') == c
    branch_dir = c / 'x/'
    branch_file = c / 'y'
    assert branch_dir == '/a/b/c/x/'
    assert e.joinpath('..', '..', 'x/') == branch_dir
    assert e.joinpath('..', '..', 'y') == branch_file


def test_read_write_memory(mem_drive: Drive):
    # A) bytes
    path = mem_drive / "file"
    path.write_bytes(b"hello world!")
    assert path.read_bytes() == b"hello world!"
    # B) text
    path = mem_drive / "file.txt"
    path.write_text("hello world!")
    assert path.read_text() == "hello world!"
    # C) a bit more fine control
    path = mem_drive / "test.txt"
    with path.open("w") as file:
        file.write("abc")
        file.write("xyz")
    with path.open("r") as file:
        assert file.read() == "abcxyz"

def test_read_write_disk(disk_drive: Drive):
    # A) bytes
    path = disk_drive / "file"
    path.write_bytes(b"hello world!")
    assert path.read_bytes() == b"hello world!"
    # B) text
    path = disk_drive / "file.txt"
    path.write_text("hello world!")
    assert path.read_text() == "hello world!"
    # C) a bit more fine control
    path = disk_drive / "test.txt"
    with path.open("w") as file:
        file.write("abc")
        file.write("xyz")
    with path.open("r") as file:
        assert file.read() == "abcxyz"

def test_nested_paths(mem_drive: Drive, disk_drive: Drive):
    for drive in (mem_drive, disk_drive):
        for path in (
            (drive / 'testfolder' / 'file.txt'),
            (drive / 'testfolder' / 'nest2' / 'nest3' / 'nest4'),
        ):
            path.write_bytes(b'123')
            assert path.read_bytes() == b'123'
        # should point to the same as the first file
        path = drive / 'testfolder' / 'unused' / '../file.txt'
        assert path == '/testfolder/file.txt'
        assert path.read_bytes() == b'123'
        print(path, path / '..', path / '..' / '..')
        path = path / '..' / '..' / 'testfolder' / 'file.txt'
        assert path == '/testfolder/file.txt'
        assert path.read_bytes() == b'123'


def test_iter(disk_drive: Drive):
    # The memory one ends up getting polluted since it uses a mutable global state, so just do it on Disk
    for name in ('file1', 'file2', 'file3'):
        (disk_drive / name).write_text("test")
    assert sorted(disk_drive.iterdir()) == [DrivePath("/file1"), DrivePath("/file2"), DrivePath("/file3")]

    for name in ('folder/a', 'folder/b/y', 'folder/b/z'):
        (disk_drive / name).write_text("test")
    assert sorted(disk_drive.iterdir()) == [
        DrivePath("/file1"), DrivePath("/file2"), DrivePath("/file3"),
        DrivePath("/folder/a"), DrivePath("/folder/b/y"), DrivePath("/folder/b/z"),
    ]
    # TODO add glob() tests once it is implemented


def test_disk_copy(disk_drive: Drive):
    inventory: DiskDriveBackend = disk_drive._drive.inventory
    copy = Drive("test_drive", drive_mode="DISK", drive_folder=inventory._root.parent)

    p1 = (disk_drive / 'file.txt')
    p2 = (copy / 'file.txt')

    p1.write_bytes(b'123')
    assert p2.read_bytes() == b'123'

def test_wrong_mode_raises(mem_drive: Drive):
    path = mem_drive / 'test'
    # TODO use more specific exceptions?
    # A) cannot specify encoding on binary mode
    with pytest.raises(Exception):
        path.open('rb', encoding='utf8')
    with pytest.raises(Exception):
        path.open('wb', encoding='utf8')
    # B) must use a context manager to read/write
    with pytest.raises(Exception):
        path.open('r').readline()
    with pytest.raises(Exception):
        path.open('rb').read()
    with pytest.raises(Exception):
        path.open('w').write('')
    with pytest.raises(Exception):
        path.open('wb').write(b'0')
    # C) cannot write on read mode | cannot read on write mode
    with pytest.raises(Exception):
        with path.open('r') as read_file:
            read_file.write('')
    with pytest.raises(Exception):
        with path.open('rb') as read_file:
            read_file.write(b'')
    with pytest.raises(Exception):
        with path.open('w') as write_file:
            write_file.read()
    with pytest.raises(Exception):
        with path.open('wb') as write_file:
            write_file.read()

