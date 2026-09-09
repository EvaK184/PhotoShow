"""Photo sources and saved selection, independent of the slideshow UI."""

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")


@dataclass(frozen=True)
class FolderSource:
    kind: str
    location: str
    label: str


@dataclass
class LoadedPhotos:
    paths: list
    cache: object = None

    def close(self):
        if self.cache is not None:
            self.cache.cleanup()


def load_local_photos(folder):
    with os.scandir(folder) as entries:
        return sorted(entry.path for entry in entries
                      if entry.name.lower().endswith(PHOTO_EXTENSIONS)
                      and entry.is_file() and os.access(entry.path, os.R_OK))


def load_source(source):
    if source.kind == "local":
        result = LoadedPhotos(load_local_photos(source.location))
    elif source.kind == "android_tree":
        result = _load_android_tree(source.location)
    else:
        raise ValueError("Unknown photo source. Please choose a folder again.")
    if not result.paths:
        result.close()
        raise ValueError("No JPG, JPEG or PNG pictures found in this folder.")
    return result


def read_source(settings_path):
    try:
        data = json.loads(Path(settings_path).read_text(encoding="utf-8"))
        source = FolderSource(**data)
        if (source.kind not in ("local", "android_tree")
                or not all(isinstance(value, str) and value
                           for value in (source.location, source.label))):
            raise ValueError("Invalid saved folder")
        return source
    except FileNotFoundError:
        return None
    except (TypeError, ValueError) as exc:
        raise ValueError("The saved folder could not be read. Choose it again.") from exc


def save_source(settings_path, source):
    path = Path(settings_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(vars(source)), encoding="utf-8")
    os.replace(temporary, path)


def _load_android_tree(location):
    # SAF returns content URIs, not filesystem paths. Stage readable files in
    # private cache for Kivy; never modify the chosen folder. A new cache per
    # selection also avoids stale image textures when reloading the same folder.
    from jnius import autoclass

    activity = autoclass("org.kivy.android.PythonActivity").mActivity
    resolver = activity.getContentResolver()
    contract = autoclass("android.provider.DocumentsContract")
    uri = autoclass("android.net.Uri").parse(location)
    children = contract.buildChildDocumentsUriUsingTree(
        uri, contract.getTreeDocumentId(uri))
    cache = tempfile.TemporaryDirectory(
        prefix="photoshow-", dir=str(activity.getCacheDir().getAbsolutePath()))
    result = LoadedPhotos([], cache)
    cursor = None
    try:
        cursor = resolver.query(children, ["document_id", "_display_name",
                                           "mime_type"], None, None, None)
        if cursor is None:
            raise OSError("The selected folder is unavailable.")
        while cursor.moveToNext():
            name = str(cursor.getString(1))
            if (not name.lower().endswith(PHOTO_EXTENSIONS)
                    or cursor.getString(2) == "vnd.android.document/directory"):
                continue
            document = contract.buildDocumentUriUsingTree(uri, cursor.getString(0))
            destination = os.path.join(cache.name,
                                       str(len(result.paths)) + Path(name).suffix.lower())
            descriptor = resolver.openFileDescriptor(document, "r")
            if descriptor is None:
                raise OSError("A picture in this folder could not be read.")
            try:
                # detachFd transfers ownership to Python, whose context manager
                # closes the descriptor even when copying fails.
                with os.fdopen(descriptor.detachFd(), "rb") as incoming:
                    with open(destination, "wb") as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
            finally:
                descriptor.close()
            result.paths.append(destination)
        return result
    except Exception:
        result.close()
        raise
    finally:
        if cursor is not None:
            cursor.close()
