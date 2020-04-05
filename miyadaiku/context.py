from __future__ import annotations


from typing import (
    TYPE_CHECKING,
    NamedTuple,
    Type,
    Sequence,
    Tuple,
    Dict,
    Union,
    Any,
    Set,
    List,
)

from abc import abstractmethod
import os, time, random, shutil
import markupsafe
from miyadaiku import ContentPath, PathTuple
from pathlib import Path, PurePosixPath

if TYPE_CHECKING:
    from .contents import Content, Article
    from .site import Site


class ContentProxy:
    def __init__(self, ctx: OutputContext, content: Content):
        self.context = ctx
        self.content = content

    def __getattr__(self, name: str) -> Any:
        return self.content.get_metadata(self.context.site, name)

    def _to_markupsafe(self, s: str) -> str:
        if not hasattr(s, "__html__"):
            s = markupsafe.Markup(s)
        return s

    @property
    def html(self) -> Union[None, str]:
        ret = self.content.build_html(self.context)
        if ret is not None:
            return self._to_markupsafe(ret)
        return None

    def load(self, target: Content) -> ContentProxy:
        ret = self.context.site.files.get_content(target.src.contentpath)
        return ContentProxy(self.context, ret)


#    def path(self, *args, **kwargs):
#        return self.context.page_content.path_to(self, *args, **kwargs)
#
#    def link(self, *args, **kwargs):
#        return self.context.page_content.link_to(self.context, self, *args, **kwargs)
#
#    def path_to(self, target, *args, **kwargs):
#        target = self.load(target)
#        return self.context.page_content.path_to(target, *args, **kwargs)
#
#    def link_to(self, target, *args, **kwargs):
#        target = self.load(target)
#        return self.context.page_content.link_to(self.context, target, *args, **kwargs)
#
#    def _to_markupsafe(self, s):
#        if not hasattr(s, "__html__"):
#            s = HTMLValue(s)
#        return s
#
#    @property
#    def abstract(self):
#        ret = self.__getattr__("abstract")
#        return self._to_markupsafe(ret)


class ConfigProxy:
    def __init__(self, ctx: "OutputContext"):
        self.context = ctx


class ContentsProxy:
    def __init__(self, ctx: "OutputContext"):
        self.context = ctx


MKDIR_MAX_RETRY = 5
MKDIR_WAIT = 0.1


def prepare_output_path(path: Path, directory: PathTuple, filename: str) -> Path:
    dir = path.joinpath(*directory)
    name = filename.strip("/\\")
    dest = os.path.expanduser((dir / name))
    dest = os.path.normpath(dest)

    s = str(path)
    if not dest.startswith(s) or dest[len(s)] not in "\\/":
        raise ValueError(f"Invalid file name: {dest}")

    dirname = os.path.split(dest)[0]
    for i in range(MKDIR_MAX_RETRY):
        if os.path.isdir(dirname):
            break
        try:
            os.makedirs(dirname, exist_ok=True)
        except IOError:
            time.sleep(MKDIR_WAIT * random.random())

    if os.path.exists(dest):
        os.unlink(dest)

    return Path(dest)


def eval_jinja(
    ctx:OutputContext,
    content: Content,
    propname: str,
    text: str,
    kwargs: Dict[str, Any],
) -> str:
    args = content.get_jinja_vars(ctx, content)
    args.update(kwargs)
    template = ctx.site.jinjaenv.from_string(text)
    template.filename = f"{content.repr_filename()}#{propname}"
    return template.render(**kwargs)


def eval_jinja_template(ctx:OutputContext, content: Content, templatename: str) -> str:
    template = ctx.site.jinjaenv.get_template(templatename)
    template.filename = templatename

    kwargs = content.get_jinja_vars(ctx, content)
    return template.render(**kwargs)


class HTMLIDInfo(NamedTuple):
    id: str
    tag: str
    text: str


class HTMLInfo(NamedTuple):
    html: str
    headers: List[HTMLIDInfo]
    header_anchors: List[HTMLIDInfo]
    fragments: List[HTMLIDInfo]


class OutputContext:
    site: Site
    contentpath: ContentPath
    content: Content
    html_cache: Dict[ContentPath, HTMLInfo]
    depends: Set[ContentPath]

    def __init__(self, site: Site, contentpath: ContentPath) -> None:
        self.site = site
        self.contentpath = contentpath
        self.content = site.files.get_content(self.contentpath)
        self.depends = set()
        self.html_cache = {}

    def get_outfilename(self) -> Path:
        dir, file = self.content.src.contentpath
        return prepare_output_path(self.site.outputdir, dir, file)

    def add_depend(self, content: Content) -> None:
        self.depends.add(content.src.contentpath)

    def get_html_cache(self, content: Content) -> Union[HTMLInfo, None]:
        return self.html_cache.get(content.src.contentpath, None)

    def set_html_cache(self, content: Content, info: HTMLInfo) -> None:
        self.html_cache[content.src.contentpath] = info

    @abstractmethod
    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        pass


class BinaryOutput(OutputContext):
    def write_body(self, outpath: Path) -> None:
        body = self.content.body
        if body is None:
            package = self.content.src.package
            if package:
                bytes = self.content.src.read_bytes()
                outpath.write_bytes(bytes)
            else:
                shutil.copyfile(self.content.src.srcpath, outpath)
        else:
            outpath.write_text(body)

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        outfilename = self.get_outfilename()
        self.write_body(outfilename)
        return [outfilename], [self.content.src.contentpath]


class JinjaOutput(OutputContext):
    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:

        templatename = self.content.get_metadata(self.site, "article_template")
        output = eval_jinja_template(self, self.content, templatename)

        outfilename = self.get_outfilename()
        outfilename.write_text(output)
        return [outfilename], [self.content.src.contentpath]


class IndexOutput(OutputContext):
    names: Tuple[str, ...]
    items: Sequence[Content]
    cur_page: int
    num_pages: int

    def __init__(
        self,
        site: Site,
        contentpath: ContentPath,
        names: Tuple[str, ...],
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        super().__init__(site, contentpath)

        self.names = names
        self.items = items
        self.cur_page = cur_page
        self.num_pages = num_pages

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        return [], []


CONTEXTS: Dict[str, Type[OutputContext]] = {
    "binary": BinaryOutput,
    "article": JinjaOutput,
    "index": IndexOutput,
}
