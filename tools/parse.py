"""Parse tool for extracting readable text from HTML."""

from __future__ import annotations

from bs4 import BeautifulSoup


def parse_html(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = " ".join(soup.get_text(" ", strip=True).split())
    return {
        "title": title,
        "content": text,
    }
