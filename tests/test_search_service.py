import tempfile
import unittest

from app.db.database import Database, DBConfig
from app.repositories.shops_repo import ShopsRepo
from app.repositories.categories_repo import CategoriesRepo
from app.repositories.products_repo import ProductsRepo
from app.services.search_service import SearchService
from app.utils import normalize


class SearchServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = Database(DBConfig(path=self.tmp.name))
        await self.db.init_schema()

        shops = ShopsRepo(self.db)
        self.shop_id = await shops.create_shop(name="Тестовый", business_type="shop")

        categories = CategoriesRepo(self.db)
        self.category_id = await categories.create(self.shop_id, "Молочные")

        products = ProductsRepo(self.db)
        await products.create(self.shop_id, self.category_id, "Молоко", 55.0, "Свежее")

        async with self.db.conn() as conn:
            await conn.execute(
                "INSERT INTO search_synonyms (term, synonym, shop_id) VALUES (?, ?, ?)",
                (normalize("молоко"), "молочко", self.shop_id),
            )
            await conn.commit()

    async def asyncTearDown(self):
        self.tmp.close()

    async def test_search_fuzzy_and_synonym(self):
        service = SearchService(self.db)
        results = await service.search_products("малако", shop_id=self.shop_id)
        self.assertTrue(results)
        self.assertEqual(results[0]["name"], "Молоко")

        results_syn = await service.search_products("молочко", shop_id=self.shop_id)
        self.assertTrue(results_syn)

    async def test_search_negative(self):
        service = SearchService(self.db)
        results = await service.search_products("несуществующий", shop_id=self.shop_id)
        self.assertEqual(results, [])
