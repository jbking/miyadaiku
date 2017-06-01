import sys
import pathlib
import importlib

from . import config
from . import contents
from . import jinjaenv
from . import output

CONFIG_FILE = 'config.yml'
CONTENTS_DIR = 'contents'
FILES_DIR = 'files'
TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'output'

class Site:
    def __init__(self, path):
        self.path = path.expanduser().resolve()
        cfgfile = path / CONFIG_FILE
        self.config = config.Config(cfgfile if cfgfile.exists() else None)

        self.contents = contents.Contents()

        self.jinjaenv = jinjaenv.create_env(
            self.config.themes, path / TEMPLATES_DIR)
        self.output = output.Outputs()

        contents.load_directory(self, path / CONTENTS_DIR)
        contents.load_directory(self, path / FILES_DIR, contents.bin_loader)
        
        for theme in self.config.themes:
            mod = importlib.import_module(theme)
            f = getattr(mod, 'load_package', None)
            if f:
                f(self)

            contents.load_package(self, theme, CONTENTS_DIR)
            contents.load_package(self, theme, FILES_DIR, contents.bin_loader)

    def build(self):
        for cont in self.contents.get_contents():
            outputs = cont.get_outputs()

            for output in outputs:
                self.output.add(output)

    def write(self):
        self.output.write(self.path / OUTPUT_DIR)


# def run():
#     dir = pathlib.Path(sys.argv[1])
#     site = Site(dir)
#     site.build()
#     site.write()


# if __name__ == "__main__":
#     happylogging.initlog(filename='-', level='DEBUG')
#     run()
