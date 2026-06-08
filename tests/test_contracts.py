import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from main import app


class RequirementsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = app.openapi()["paths"]
        cls.html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    def test_all_categories_have_crud_search_detail_and_count(self):
        self.assertIn("/universo/{tipo}/cantidad", self.paths)
        for category in ["personajes", "casas", "hechizos", "eventos", "peliculas", "objetos"]:
            self.assertIn(f"/universo/{category}", self.paths)
            self.assertIn(f"/universo/{category}/buscar", self.paths)
            self.assertIn(f"/universo/{category}/{{item_id}}", self.paths)
            self.assertEqual(
                {"get", "post"},
                set(self.paths[f"/universo/{category}"].keys()),
            )
            self.assertEqual(
                {"get", "put", "delete"},
                set(self.paths[f"/universo/{category}/{{item_id}}"].keys()),
            )

    def test_relationship_endpoints_exist(self):
        for path in [
            "/universo/asociaciones/eventos",
            "/universo/asociaciones/peliculas",
            "/universo/asociaciones/peliculas-eventos",
        ]:
            self.assertEqual({"post", "delete"}, set(self.paths[path].keys()))

    def test_frontend_has_search_and_pagination_for_every_category(self):
        for category in ["personajes", "casas", "hechizos", "eventos", "peliculas", "objetos"]:
            self.assertIn(f'id="search-{category}"', self.html)
            self.assertIn(f'id="{category}-pagination"', self.html)

    def test_frontend_has_detail_and_all_admin_relationships(self):
        self.assertIn('id="detail-modal"', self.html)
        self.assertIn("showDetail(", self.js)
        self.assertIn('id="relation-work-add"', self.html)
        self.assertIn("changeWorkEventRelation", self.js)

    def test_integrity_and_load_audit_tools_exist(self):
        audit = ROOT / "backend" / "seed" / "audit_consistency.py"
        load_test = ROOT / "scripts" / "load_test.py"
        self.assertTrue(audit.exists())
        self.assertTrue(load_test.exists())
        self.assertIn("_validate_character_references", (ROOT / "backend" / "routes" / "universo.py").read_text())


if __name__ == "__main__":
    unittest.main()
