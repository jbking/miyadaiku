import os
import pathlib
import time
import collections

MKDIR_MAX_RETRY = 5
MKDIR_WAIT = 0.05


class Output:
    def __init__(self, dirname, name, stat, body, context):
        assert name
        self.dirname = dirname
        self.name = name
        self.body = body
        self.stat = stat
        self.context = context

    def write(self, path):
        dir = path.joinpath(*self.dirname)

        for i in range(MKDIR_MAX_RETRY):
            if dir.is_dir():
                break
            try:
                dir.mkdir(parents=True)
            except FileExistsError:
                pass
            time.sleep(MKDIR_WAIT)

        name = self.name.strip('/\\')
        dest = os.path.expanduser((dir / name))
        dest = os.path.normpath(dest)

        s = str(path)
        if not dest.startswith(s) or dest[len(s)] not in '\\/':
            raise ValueError(f"Invalid file name: {self.name}")

        destfile = pathlib.Path(dest)
        destfile.write_bytes(self.body)

        if self.stat:
            os.utime(dest, (self.stat.st_atime, self.stat.st_mtime))
            os.chmod(dest, self.stat.st_mode)

        return destfile

class Outputs:
    def __init__(self):
        self._files = {}

    def add(self, output):
        self._files[(output.dirname, output.name)] = output

    def write(self, path):
        deps = collections.defaultdict(list)
        for output in self._files.values():
            created = output.write(path)

            rel = created.relto(path)
            for src in output.context.depends:
                deps[(src.dirname, src.name)].add(
                    (str(created), rel))

        return dict(deps)
