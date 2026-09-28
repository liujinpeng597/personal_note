import pytest

from app.utils.markdown_render import render_markdown


@pytest.mark.parametrize("payload", [
    "<script>alert(1)</script>",
    '<img src=x onerror=alert(1)>',
    "[x](javascript:alert(1))",
    '<a href="#" onclick="alert(1)">x</a>',
    '<iframe src="//evil"></iframe>',
])
def test_xss_is_stripped(payload):
    out = render_markdown(payload)
    assert "onerror" not in out.lower()
    assert "onclick" not in out.lower()
    assert "javascript:" not in out.lower()
    assert "iframe" not in out.lower()
    assert "<script" not in out.lower()


def test_normal_markdown_renders():
    out = render_markdown("# 标题\n\n- 一\n- 二\n\n```python\nprint(1)\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert "<h1>" in out
    assert "<ul>" in out
    assert "<table>" in out
    assert "print(1)" in out


def test_empty_input_returns_empty_string():
    assert render_markdown("") == ""
    assert render_markdown(None) == ""


def test_links_and_images_keep_safe_attributes():
    out = render_markdown("[站点](https://example.com)\n\n![图](https://example.com/a.png)")
    assert 'href="https://example.com"' in out
    assert 'src="https://example.com/a.png"' in out
