"""Shared catalog presentation rules; independent of platform adapters."""
import re
from dataclasses import replace


def normalize_catalog_items(items):
    seen = set()
    result = []
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        title = re.sub(r'\s+', ' ', item.title or '').strip()
        # Only normalize episode/navigation-only labels, never erase real work titles.
        match = re.fullmatch(r'[«»<>‹›\s]*(?:(?:上一集|下一集)\s*[（(]?)?第\s*(\d+)\s*集[）)\s«»<>‹›]*', title)
        if match:
            title = f'第{int(match.group(1))}集'
        result.append(replace(item, title=title))
    return result
