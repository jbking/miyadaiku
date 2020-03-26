from typing import (
    List,
    Dict,
    Any,
    Set,
    Callable,
    Iterator,
    Tuple
)
import sys
import os
from pathlib import Path
import importlib
import importlib.util
import importlib.abc
import yaml
import pkg_resources
import dateutil
import miyadaiku
from .config import Config
from .loader import ContentFiles, loadfiles
from .jinjaenv import create_env


def timestamp_constructor(loader, node): # type: ignore 
    return dateutil.parser.parse(node.value)

yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor) # type: ignore 


def _import_script(name:str, path:Path)->Any:
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)

    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(m)
    sys.modules[name] = m
    return m

class Site:
    root: Path
    sitecondig: Dict[str, Any]
    config: Config
    files: ContentFiles
    ignores: Set[str]
    themes: List[str]

    def _load_config(self, props: Dict[str, Any])->None:
        cfgfile = self.root / miyadaiku.CONFIG_FILE
        self.siteconfig = (
            yaml.load(
                cfgfile.read_text(encoding=miyadaiku.YAML_ENCODING),
                Loader=yaml.FullLoader,
            )
            or {}
        )
        self.siteconfig.update(props)

        self.config = Config(self.siteconfig)
        self.stat_config = os.stat(cfgfile) if cfgfile.exists() else None

        self.ignores = set(self.siteconfig.get("ignores", []))

    def _load_themes(self)->None:
        def _load_theme_config(package:str)->Dict[str, Any]:
            try:
                s = pkg_resources.resource_string(package, miyadaiku.CONFIG_FILE)
            except FileNotFoundError:
                cfg = {}
            else:
                cfg = yaml.load(s.decode(miyadaiku.YAML_ENCODING), Loader=yaml.FullLoader)

            if not cfg:
                cfg = {}
            return cfg


        def _load_theme_configs(themes: List[str])->Iterator[Tuple[str, Dict[str, Any]]]:
            seen = set()
            themes = themes[:]
            while themes:
                theme = themes.pop(0)
                if theme in seen:
                    continue
                seen.add(theme)

                cfg = _load_theme_config(theme)
                themes = list(t for t in cfg.get('themes', [])) + themes
                yield theme, cfg


        self.themes = []
        for theme, cfg in _load_theme_configs(self.siteconfig.get("themes", [])):
            self.themes.append(theme)
            self.config.add_themecfg(cfg)


    def _load_jinjaenv(self)->None:
        self.jinjaenv = create_env(
            self, self.themes, [self.root / miyadaiku.TEMPLATES_DIR])


    def _import_themes(self)->None:
        for theme in self.themes:
            mod = importlib.import_module(theme)
            f = getattr(mod, 'load_package', None)
            if f:
                f(self)

    def _load_jinja_globals(self)->None:
        import miyadaiku.extend
        for name, value in miyadaiku.extend._jinja_globals.items():
            self.add_jinja_global(name, value)

    def _load_modules(self)->None:
        modules = (self.root / miyadaiku.MODULES_DIR).resolve()
        if modules.is_dir():
            s = str(modules)
            if s not in sys.path:
                sys.path.insert(0, s)

            for f in modules.iterdir():
                if not f.is_file():
                    continue
                if f.suffix != '.py':
                    continue
                name = f.stem
                if not name.isidentifier():
                    continue
                m = _import_script(name, f)

                self.add_jinja_global(name, m)

    def add_template_module(self, name:str, templatename:str)->None:
        template = self.jinjaenv.get_template(templatename)
        self.jinjaenv.globals[name] = template.module

    def add_jinja_global(self, name:str, f:Callable[..., Any])->None:
        self.jinjaenv.globals[name] = f

    def load(self, root:Path, props: Dict[str, Any])->None:
        self.root = root
        self._load_config(props)
        self._load_themes()
        self._load_jinjaenv()
        self._import_themes()
        self._load_jinja_globals()
        self._load_modules()

        loadfiles(
            self.files,
            self.config,
            self.root,
            self.ignores,
            self.themes)
        