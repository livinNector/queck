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


class Merger:
    def __init__(self, extend_lists=True, extend_dicts=True):
        self.extend_lists = extend_lists
        self.extend_dicts = extend_dicts

    def merge(self, a, b):
        if isinstance(b, list):
            for i in range(min(len(a), len(b))):
                if not isinstance(b[i], (list, dict)):
                    a[i] = b[i]
                else:
                    self.merge(a[i], b[i])
            if self.extend_lists:
                a.extend(b[len(a) :])
        elif isinstance(b, dict):
            a_keys = set(a.keys())
            for k in a_keys:
                if k in b:
                    if not isinstance(b[k], (list, dict)):
                        a[k] = b[k]
                    else:
                        self.merge(a[k], b[k])
            if self.extend_dicts:
                for k in b.keys():
                    if k not in a_keys:
                        a[k] = b[k]
