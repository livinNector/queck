import os


def safe_write_file(file_name, content, format=None, force=False):
    """Writes to a file without overwriting it."""
    if format is not None:
        base, ext = os.path.splitext(file_name)
        file_name = f"{base}.{format}"

    if os.path.exists(file_name) and not force:
        raise FileExistsError(f"{file_name} already exists. ")
    with open(file_name, "w") as f:
        f.write(content)


def write_file(file_name, content, format=None):
    safe_write_file(file_name, content, format, force=True)
