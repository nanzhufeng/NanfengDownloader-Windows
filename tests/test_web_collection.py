import unittest
from app.web_collection import episode_links
from app.catalog import CatalogItem


class CollectionTests(unittest.TestCase):
    def test_navigation_labels_use_episode_number(self):
        result = episode_links('https://yhdm.one/vod-play/123/ep1177.html', [
            ('/vod-play/123/ep1176.html', '«上一集(第1176集)'),
            ('/vod-play/123/ep1176.html', '第1176集'),
            ('/vod-play/123/ep1177.html', '下一集')], 500)
        self.assertEqual([title for _, title in result], ['第1176集', '第1177集'])

    def test_group_selection_and_last_partial_group(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from app.collection_dialog import CollectionDialog
        app = QApplication.instance() or QApplication([])
        dialog = CollectionDialog([CatalogItem('其他网站', str(i), f'https://example.org/{i}') for i in range(12)])
        dialog.list.group_size = 5
        dialog.list.apply_group(6, Qt.Checked)
        self.assertEqual([x.title for x in dialog.selected()], ['5','6','7','8','9'])
        dialog.check_visible(False)
        dialog.list.group_size = 10
        dialog.list.apply_group(11, Qt.Checked)
        self.assertEqual([x.title for x in dialog.selected()], ['10','11'])
        dialog.close()
    def test_play_page_reads_only_same_series(self):
        result = episode_links('https://yhdm.one/vod-play/123/ep10.html', [
            ('/vod-play/123/ep10.html', '第10集'), ('/vod-play/999/ep1.html', '推荐作品'),
            ('/vod-play/123/ep2.html', '第2集')], 500)
        self.assertEqual([title for _, title in result], ['第2集', '第10集'])

    def test_direct_manifest_does_not_expand_collection(self):
        from app.web_collection import discover_collection
        self.assertIsNone(discover_collection('https://bfikuncdn.com/20260906/BcW0QcaA/index.m3u8', 500))
    def test_filters_other_works_and_sorts_numerically(self):
        result = episode_links('https://yhdm.one/vod/123.html', [
            ('/vod-play/123/ep10.html', '第10集'), ('/vod-play/999/ep1.html', '其他'),
            ('https://other.test/vod-play/123/ep1.html', '广告'), ('/vod-play/123/ep2.html', '第2集')], 500)
        self.assertEqual([title for _, title in result], ['第2集', '第10集'])

    def test_home_with_multiple_collections_requires_specific_url(self):
        with self.assertRaises(RuntimeError):
            episode_links('https://yhdm.one/', [('/vod-play/123/ep1.html', 'a'), ('/vod-play/456/ep1.html', 'b')], 500)

    def test_dialog_filters_and_preserves_selection(self):
        from PySide6.QtWidgets import QApplication
        from app.collection_dialog import CollectionDialog
        app = QApplication.instance() or QApplication([])
        dialog = CollectionDialog([CatalogItem('其他网站', f'第{i}集', f'https://example.org/{i}') for i in range(3)])
        dialog.filter('第1集')
        dialog.check_visible(True)
        self.assertEqual([item.title for item in dialog.selected()], ['第1集'])
        dialog.filter('')
        self.assertEqual(len(dialog.selected()), 1)
        dialog.check_visible(False)
        self.assertEqual(dialog.selected(), [])
        dialog.close()
