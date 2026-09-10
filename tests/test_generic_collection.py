import unittest
from app.generic_collection import catalog_from_info, is_collection_candidate


class GenericCollectionTests(unittest.TestCase):
    def test_collection_routes_but_single_video_stays_fast(self):
        self.assertTrue(is_collection_candidate('https://vimeo.com/showcase/123'))
        self.assertTrue(is_collection_candidate('https://example.org/series/123'))
        self.assertFalse(is_collection_candidate('https://vimeo.com/123'))
        self.assertFalse(is_collection_candidate('https://example.org/file.m3u8'))

    def test_only_individual_http_links_are_imported(self):
        result = catalog_from_info({'_type':'playlist','entries':[
            {'title':'a','url':'https://example.org/1'},
            {'title':'duplicate','url':'https://example.org/1'},
            {'title':'bad','url':'file:///secret'},
            {'title':'nested','url':'https://example.org/list','_type':'playlist'},
            {'title':'b','url':'https://example.org/2'}]}, 'https://example.org/series/1', 500)
        self.assertEqual([x.title for x in result], ['a','b'])

    def test_lazy_catalog_is_bounded(self):
        consumed = []
        def entries():
            for i in range(1000):
                consumed.append(i)
                yield {'url':f'https://example.org/{i}'}
        result = catalog_from_info({'_type':'playlist','entries':entries()},'https://example.org/list', 10)
        self.assertEqual(len(result),10)
        self.assertEqual(len(consumed),10)
