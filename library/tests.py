from django.db import connection
from rest_framework.test import APITestCase


class BookEndpointTests(APITestCase):
    url = "/api/livros/"

    def book(self, **changes):
        return {
            "titulo": "Python Fluente",
            "autor": "Luciano Ramalho",
            "data_publicacao": "2022-05-10",
            "resumo": "Programação idiomática em Python.",
        } | changes

    def create(self, **changes):
        response = self.client.post(self.url, self.book(**changes), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.data

    def test_create_and_read_persisted_book(self):
        created = self.create()
        self.assertIsInstance(created["id"], int)
        self.assertEqual({k: created[k] for k in self.book()}, self.book())
        # Outra requisição deve ler o registro persistido.
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [created])

    def test_required_fields(self):
        for field in self.book():
            for invalid in ("missing", "", "   ", None):
                with self.subTest(field=field, invalid=invalid):
                    payload = self.book()
                    if invalid == "missing":
                        del payload[field]
                    else:
                        payload[field] = invalid
                    response = self.client.post(self.url, payload, format="json")
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(field, response.data)
        self.assertEqual(self.client.get(self.url).data, [])

    def test_invalid_dates(self):
        for value in ("2023-02-29", "2024-13-01", "31/12/2020", "ontem"):
            with self.subTest(value=value):
                response = self.client.post(
                    self.url, self.book(data_publicacao=value), format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("data_publicacao", response.data)

    def test_valid_leap_day(self):
        self.create(data_publicacao="2024-02-29")

    def test_field_length_limits(self):
        for field, length in (("titulo", 255), ("autor", 255), ("resumo", 10000)):
            with self.subTest(field=field):
                response = self.client.post(
                    self.url, self.book(**{field: "x" * (length + 1)}), format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)

    def test_partial_case_insensitive_filters(self):
        expected = self.create(titulo="INTRODUÇÃO À PROGRAMAÇÃO", autor="ÁLVARO Silva")
        self.create(titulo="Redes", autor="Outra pessoa")
        for params in ({"titulo": " programação "}, {"autor": "álvaro"}):
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data, [expected])

    def test_combined_filters_use_and(self):
        expected = self.create()
        self.create(titulo="Python Básico", autor="Outro autor")
        self.create(titulo="Outro livro", autor="Luciano Ramalho")
        response = self.client.get(self.url, {"titulo": "python", "autor": "ramalho"})
        self.assertEqual(response.data, [expected])

    def test_empty_and_missing_filters_list_all(self):
        expected = self.create()
        self.assertEqual(self.client.get(self.url).data, [expected])
        self.assertEqual(
            self.client.get(self.url, {"titulo": " ", "autor": ""}).data, [expected]
        )

    def test_no_matches_returns_empty_list(self):
        self.create()
        response = self.client.get(self.url, {"titulo": "inexistente"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_filter_is_literal_and_accents_are_significant(self):
        expected = self.create(titulo="Python 3.12")
        self.create(titulo="Python 3x12", autor="Álvaro")
        self.assertEqual(self.client.get(self.url, {"titulo": "3.12"}).data, [expected])
        self.assertEqual(self.client.get(self.url, {"autor": "alvaro"}).data, [])

    def test_empty_library(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_write_methods_outside_scope_are_not_allowed(self):
        for method in (self.client.put, self.client.patch, self.client.delete):
            self.assertEqual(method(self.url, {}, format="json").status_code, 405)

    def test_database_is_in_memory(self):
        self.assertIn("memory", connection.settings_dict["NAME"])
