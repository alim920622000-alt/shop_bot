import unittest

from app.services.import_service import parse_products_csv


class ImportServiceTests(unittest.TestCase):
    def test_parse_products_csv_success(self):
        content = "name,price,description\nХлеб,10,Белый\nМолоко,55,\n"
        result = parse_products_csv(content)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.rows), 2)
        self.assertEqual(result.rows[0].name, "Хлеб")

    def test_parse_products_csv_duplicate_and_invalid(self):
        content = "name;price\nХлеб;10\nХлеб;12\nСахар;abc\n"
        result = parse_products_csv(content)
        self.assertTrue(result.errors)
