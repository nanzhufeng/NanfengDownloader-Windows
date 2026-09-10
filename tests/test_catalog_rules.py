import unittest
from app.catalog import CatalogItem
from app.catalog_rules import normalize_catalog_items


class SharedCatalogRulesTests(unittest.TestCase):
    def test_rules_apply_to_every_platform_without_rewriting_titles(self):
        for platform in ('YouTube', '抖音', '哔哩哔哩', '小红书', 'TikTok', '其他网站'):
            items = [CatalogItem(platform, '«上一集(第001集)', 'https://example.org/1'),
                     CatalogItem(platform, '第1集', 'https://example.org/1'),
                     CatalogItem(platform, '教程 第2集 模型训练', 'https://example.org/2')]
            result = normalize_catalog_items(items)
            self.assertEqual([x.title for x in result], ['第1集', '教程 第2集 模型训练'])
