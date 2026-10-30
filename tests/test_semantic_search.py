import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import numpy as np

from semantic_search.service import (
    SemanticSearch,
    build_index,
    embed,
    preprocess,
    read_documents,
)


class FakeEncoder:
    """Vetores conhecidos testam o ranking/FAISS, sem simular qualidade linguística."""

    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append(list(texts))
        vectors = {
            "primeiro": [4, 0],
            "segundo": [3, 3],
            "terceiro": [0, 5],
            "consulta": [7, 0],
        }
        return np.array([vectors[text] for text in texts], dtype=np.float64)


class SemanticSearchTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.documents_path = self.root / "documents.json"
        self.index_dir = self.root / "index"
        self.documents = [
            {"id": str(i), "text": text}
            for i, text in enumerate(("primeiro", "segundo", "terceiro"))
        ]
        self.documents_path.write_text(json.dumps(self.documents), encoding="utf-8")
        self.encoder = FakeEncoder()

    def build(self):
        self.assertEqual(
            build_index(self.documents_path, self.index_dir, encoder=self.encoder), 3
        )

    def test_persist_reload_ranking_scores_and_no_document_reembedding(self):
        self.build()
        # A consulta usa o snapshot persistido mesmo se o corpus for removido.
        self.documents_path.unlink()
        query_encoder = FakeEncoder()
        search = SemanticSearch(self.index_dir, encoder=query_encoder)
        results = search.search("consulta", top_k=2)
        self.assertEqual([result["id"] for result in results], ["0", "1"])
        self.assertEqual(results[0]["text"], "primeiro")
        self.assertAlmostEqual(results[0]["score"], 1.0, places=6)
        self.assertAlmostEqual(results[1]["score"], 2**-0.5, places=6)
        search.search("consulta", top_k=1)
        self.assertEqual(query_encoder.calls, [["consulta"], ["consulta"]])
        self.assertEqual(self.encoder.calls, [["primeiro", "segundo", "terceiro"]])

    def test_top_k_larger_than_corpus_does_not_repeat_results(self):
        self.build()
        results = SemanticSearch(self.index_dir, encoder=self.encoder).search(
            "consulta", 50
        )
        self.assertEqual(len(results), 3)
        self.assertEqual(len({result["id"] for result in results}), 3)

    def test_invalid_query_and_top_k(self):
        self.build()
        search = SemanticSearch(self.index_dir, encoder=self.encoder)
        for query, top_k in (
            ("", 1),
            (" ", 1),
            (None, 1),
            ("consulta", 0),
            ("consulta", -1),
            ("consulta", 1.5),
            ("consulta", True),
        ):
            with self.subTest(query=query, top_k=top_k), self.assertRaises(ValueError):
                search.search(query, top_k)

    def test_missing_index_does_not_download_model(self):
        with patch("semantic_search.service.load_encoder") as load:
            with self.assertRaisesRegex(ValueError, "Índice ausente"):
                SemanticSearch(self.index_dir)
            load.assert_not_called()

    def test_corrupt_index_is_detected_before_loading_model(self):
        self.build()
        (self.index_dir / "index.faiss").write_bytes(b"corrupted")
        with patch("semantic_search.service.load_encoder") as load:
            with self.assertRaisesRegex(ValueError, "incompatíveis"):
                SemanticSearch(self.index_dir)
            load.assert_not_called()

    def test_incompatible_model_revision(self):
        self.build()
        path = self.index_dir / "metadata.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["model_revision"] = "different-revision"
        path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "incompatíveis"):
            SemanticSearch(self.index_dir, encoder=self.encoder)

    def test_invalid_corpus(self):
        for documents in (
            [],
            {},
            [{"id": "a", "text": " "}],
            [{"id": "a"}],
            [{"id": "a", "text": "x"}, {"id": "a", "text": "y"}],
        ):
            with self.subTest(documents=documents):
                self.documents_path.write_text(json.dumps(documents), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_documents(self.documents_path)

    def test_preprocessing_preserves_accents_and_python(self):
        self.assertEqual(
            preprocess("  ação\n frutas.append('maçã')  "), "ação frutas.append('maçã')"
        )

    def test_zero_vectors_are_rejected(self):
        with patch.object(self.encoder, "encode", return_value=np.zeros((1, 2))):
            with self.assertRaisesRegex(ValueError, "inválidos"):
                embed(self.encoder, ["consulta"])

    def test_long_text_is_not_silently_truncated(self):
        self.encoder.tokenizer = lambda *_args, **_kwargs: {"input_ids": [[1, 2, 3]]}
        self.encoder.max_seq_length = 2
        with self.assertRaisesRegex(ValueError, "janela"):
            embed(self.encoder, ["consulta"])
