import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_hub(path):
    loader=importlib.machinery.SourceFileLoader("library_hub_test",str(path))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.root=Path(__file__).resolve().parents[1]
        self.hub=load_hub(self.root/"bin/khaos-hub")
        self.temp=tempfile.TemporaryDirectory()
        self.hub.STATE=Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_save_update_delete_and_private_database(self):
        first=self.hub.library_save({"title":"IR field guide","url":"https://example.org/ir","kind":"research","tags":"ir","note":"triage"})
        self.assertEqual(len(first["items"]),1)
        item=first["items"][0]
        self.assertEqual(item["title"],"IR field guide")
        self.hub.library_save({"id":item["id"],"title":"Updated","url":"","kind":"bookmark","tags":"","note":""})
        self.assertEqual(self.hub.library_list()["items"][0]["title"],"Updated")
        self.assertEqual(self.hub.library_delete({"id":item["id"]})["items"],[])
        self.assertTrue((self.hub.STATE/"library.sqlite3").exists())

    def test_reject_bad_urls_credentials_and_oversized_fields(self):
        for url in ("javascript:alert(1)","file:///etc/passwd","https://user:pass@example.org/"):
            with self.assertRaises(ValueError):
                self.hub.library_save({"title":"bad","url":url})
        with self.assertRaises(ValueError):
            self.hub.library_save({"title":"x"*181})

    def test_source_routes_and_local_boundary(self):
        source=(self.root/"apps/khaos-hub/web/index.html").read_text()
        self.assertIn('data-page="library"',source)
        self.assertIn('id="library-list"',source)
        js=(self.root/"apps/khaos-hub/web/app.js").read_text()
        self.assertIn('textContent=item.title',js)
        self.assertIn('/api/library/save',js)
        self.assertNotIn("history.",js)
        self.assertNotIn("document.cookie",js)


if __name__=="__main__":
    unittest.main()
