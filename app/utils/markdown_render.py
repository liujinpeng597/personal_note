"""Markdown → HTML → nh3 白名单消毒。全站唯一产出 HTML 的地方。"""
import markdown as markdown_lib
import nh3

ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "del", "code", "pre", "blockquote",
    "ul", "ol", "li", "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "code": {"class"},
}

ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_markdown(text):
    if not text:
        return ""
    html = markdown_lib.markdown(text, extensions=["extra", "sane_lists", "nl2br"])
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
    )
