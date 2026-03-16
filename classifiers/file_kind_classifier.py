"""Classifier for non-language repository files such as archives and certificates."""

import os


FILE_KIND_BY_EXTENSION = {
    ".7z": "Archive",
    ".apk": "Package",
    ".a": "Binary",
    ".bin": "Binary",
    ".bz2": "Archive",
    ".cer": "Certificate",
    ".class": "Binary",
    ".crt": "Certificate",
    ".csr": "Certificate",
    ".csv": "Dataset",
    ".dat": "Dataset",
    ".db": "Database",
    ".der": "Certificate",
    ".dll": "Binary",
    ".doc": "Document",
    ".docx": "Document",
    ".ear": "Archive",
    ".exe": "Binary",
    ".gif": "Image",
    ".gz": "Archive",
    ".ico": "Image",
    ".ipa": "Package",
    ".jar": "Archive",
    ".jks": "Certificate",
    ".jpeg": "Image",
    ".jpg": "Image",
    ".key": "Certificate",
    ".keystore": "Certificate",
    ".lib": "Binary",
    ".lock": "Lockfile",
    ".log": "Log",
    ".mov": "Video",
    ".mp3": "Audio",
    ".mp4": "Video",
    ".nar": "Archive",
    ".o": "Binary",
    ".obj": "Binary",
    ".odp": "Document",
    ".ods": "Document",
    ".odt": "Document",
    ".p12": "Certificate",
    ".pem": "Certificate",
    ".pdf": "Document",
    ".pfx": "Certificate",
    ".png": "Image",
    ".ppt": "Document",
    ".pptx": "Document",
    ".pub": "Certificate",
    ".rar": "Archive",
    ".rtf": "Document",
    ".so": "Binary",
    ".sqlite": "Database",
    ".sqlite3": "Database",
    ".svg": "Image",
    ".tar": "Archive",
    ".tgz": "Archive",
    ".tif": "Image",
    ".tiff": "Image",
    ".war": "Archive",
    ".wav": "Audio",
    ".webp": "Image",
    ".whl": "Archive",
    ".xls": "Document",
    ".xlsx": "Document",
    ".xz": "Archive",
    ".zip": "Archive",
}

FILE_KIND_BY_FILENAME = {
    "id_dsa": "Certificate",
    "id_ecdsa": "Certificate",
    "id_ed25519": "Certificate",
    "id_rsa": "Certificate",
    "known_hosts": "Certificate",
}


class FileKindClassifier:
    """Maps common non-language repository files to stable file-kind labels."""

    def detect_kind(self, path: str) -> str | None:
        filename = os.path.basename(path).lower()
        if filename:
            kind = FILE_KIND_BY_FILENAME.get(filename)
            if kind:
                return kind

        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if not ext:
            return None

        return FILE_KIND_BY_EXTENSION.get(ext)
