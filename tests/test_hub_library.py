import importlib.machinery
import importlib.util
import json
import sqlite3
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
        db=sqlite3.connect(self.hub.STATE/"library.sqlite3")
        self.assertIn("sources", {row[1] for row in db.execute("PRAGMA table_info(library)")})
        db.close()

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
        self.assertIn('title.textContent = item.title',js)
        self.assertIn('/api/library/save',js)
        self.assertIn('/api/library/browser-import',js)
        self.assertNotIn("history.",js)
        self.assertNotIn("document.cookie",js)
        css=(self.root/"apps/khaos-hub/web/app.css").read_text()
        self.assertIn(".library-form,.library-tools { padding: 13px; gap: 9px; border-radius: 14px; }",css)

    def test_batch_import_merges_normalized_urls_and_sources(self):
        self.hub.library_save({"title":"Keep my title","url":"https://EXAMPLE.org:443/","kind":"research","note":"curated"})
        result=self.hub.library_import_items([
            {"title":"First browser title","url":"https://example.org","kind":"bookmark","sources":[{"browser":"Brave","profile":"Default","folder":"Bookmarks bar","title":"First browser title"}]},
            {"title":"Reading title","url":"https://example.org/","kind":"reading","sources":[{"browser":"Firefox","profile":"Profile 1","folder":"Read later","title":"Reading title"}]},
        ], source_label="")
        self.assertEqual(result["added"],0)
        self.assertEqual(result["merged"],1)
        self.assertEqual(result["duplicates_in_batch"],1)
        item=result["items"][0]
        self.assertEqual(item["title"],"Keep my title")
        self.assertEqual(item["note"],"curated")
        self.assertEqual(item["kind"],"research")
        self.assertEqual({source["browser"] for source in item["sources"]},{"Brave","Firefox"})

    def test_chromium_parser_keeps_folder_provenance_and_reading_type(self):
        bookmarks=Path(self.temp.name)/"Bookmarks"
        bookmarks.write_text(json.dumps({"roots":{"bookmark_bar":{"name":"Bookmarks bar","type":"folder","children":[
            {"name":"Read later","type":"folder","children":[{"name":"Paper","type":"url","url":"https://example.org/paper"}]}
        ]}}}))
        items=self.hub.read_chromium_bookmarks(bookmarks,"Brave","Default")
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["kind"],"reading")
        self.assertEqual(items[0]["sources"][0]["folder"],"Bookmarks bar / Read later")

    def test_firefox_parser_uses_bookmarks_only_and_preserves_folder(self):
        path=Path(self.temp.name)/"places.sqlite"
        db=sqlite3.connect(path)
        db.executescript("""
          CREATE TABLE moz_places(id INTEGER PRIMARY KEY,url TEXT,title TEXT);
          CREATE TABLE moz_bookmarks(id INTEGER PRIMARY KEY,parent INTEGER,title TEXT,type INTEGER,fk INTEGER);
          INSERT INTO moz_places VALUES(1,'https://example.org/guide','Guide');
          INSERT INTO moz_places VALUES(2,'https://history.example/','History only');
          INSERT INTO moz_bookmarks VALUES(1,0,'root',2,NULL);
          INSERT INTO moz_bookmarks VALUES(2,1,'Read Later',2,NULL);
          INSERT INTO moz_bookmarks VALUES(3,2,'Saved Guide',1,1);
        """)
        db.commit(); db.close()
        items=self.hub.read_firefox_bookmarks(path,"Firefox","Profile 1")
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]["kind"],"reading")
        self.assertIn("Read Later",items[0]["sources"][0]["folder"])
        self.assertFalse((self.hub.STATE/"library.sqlite3").exists())

    def test_import_is_atomic_on_invalid_item_and_normalizes_defaults(self):
        with self.assertRaises(ValueError):
            self.hub.library_import_items([
                {"title":"Valid","url":"https://example.org"},
                {"title":"Invalid","url":"javascript:alert(1)"},
            ])
        self.assertEqual(self.hub.library_list()["items"],[])
        empty=self.hub.library_import_items([], source_label="")
        self.assertEqual(empty["added"],0)


if __name__=="__main__":
    unittest.main()
