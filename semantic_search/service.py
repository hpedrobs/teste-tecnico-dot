"""Embeddings locais e índice exato de similaridade de cosseno, persistido em disco."""

import hashlib
import json
from pathlib import Path

import faiss
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCUMENTS = ROOT / "data" / "documents.json"
DEFAULT_INDEX_DIR = ROOT / "artifacts" / "semantic_index"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Revisão fixa evita trocar silenciosamente os pesos entre indexação e consulta.
MODEL_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"


def load_encoder(model_name=MODEL_NAME, revision=MODEL_REVISION):
    # Import tardio: testar índice e validações não exige carregar o PyTorch.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name, revision=revision, device="cpu")


def preprocess(text):
    """Uniformiza espaços sem remover acentos, pontuação ou sintaxe Python."""
    return " ".join(text.split())


def read_documents(path):
    documents = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(documents, list) or not documents:
        raise ValueError("O corpus deve ser uma lista não vazia de documentos.")
    seen = set()
    for document in documents:
        if not isinstance(document, dict) or any(
            not isinstance(document.get(field), str) or not document[field].strip()
            for field in ("id", "text")
        ):
            raise ValueError(
                "Cada documento deve conter id e text como textos não vazios."
            )
        if document["id"] in seen:
            raise ValueError(f"Identificador de documento duplicado: {document['id']}")
        seen.add(document["id"])
    return documents


def embed(encoder, texts):
    texts = [preprocess(text) for text in texts]
    # Este modelo tem janela curta. Recusar truncamento evita indexar apenas
    # parte do conteúdo sem avisar. O corpus entregue cabe na janela de tokens.
    if hasattr(encoder, "tokenizer"):
        tokens = encoder.tokenizer(texts, truncation=False, padding=False)["input_ids"]
        if any(len(sequence) > encoder.max_seq_length for sequence in tokens):
            raise ValueError(
                "Texto excede a janela do modelo. Divida-o em documentos menores antes de indexar/consultar."
            )
    vectors = np.ascontiguousarray(
        encoder.encode(texts, convert_to_numpy=True, show_progress_bar=False),
        dtype=np.float32,
    )
    if (
        vectors.ndim != 2
        or vectors.shape[0] != len(texts)
        or vectors.shape[1] == 0
        or not np.isfinite(vectors).all()
        or np.any(np.linalg.norm(vectors, axis=1) == 0)
    ):
        raise ValueError("O modelo retornou embeddings inválidos.")
    # Produto interno de vetores unitários equivale a similaridade de cosseno.
    # A mesma função é usada para documentos e consultas.
    faiss.normalize_L2(vectors)
    return vectors


def build_index(
    documents_path=DEFAULT_DOCUMENTS, index_dir=DEFAULT_INDEX_DIR, *, encoder=None
):
    documents = read_documents(documents_path)
    if encoder is None:
        encoder = load_encoder()
    vectors = embed(encoder, [document["text"] for document in documents])
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    index_bytes = faiss.serialize_index(index).tobytes()
    metadata = {
        "version": 1,
        "model_name": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "metric": "cosine",
        "dimension": index.d,
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "documents": documents,
    }
    (index_dir / "index.faiss").write_bytes(index_bytes)
    # Se a gravação for interrompida, o checksum impede usar um par inconsistente.
    (index_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(documents)


class SemanticSearch:
    """Carrega índice/modelo uma vez; cada search calcula só o vetor da consulta."""

    def __init__(self, index_dir=DEFAULT_INDEX_DIR, *, encoder=None):
        index_dir = Path(index_dir)
        try:
            metadata = json.loads(
                (index_dir / "metadata.json").read_text(encoding="utf-8")
            )
            index_bytes = (index_dir / "index.faiss").read_bytes()
        except FileNotFoundError as error:
            raise ValueError(
                "Índice ausente. Execute: python -m semantic_search index"
            ) from error
        if (
            not isinstance(metadata, dict)
            or metadata.get("version") != 1
            or metadata.get("metric") != "cosine"
            or metadata.get("model_name") != MODEL_NAME
            or metadata.get("model_revision") != MODEL_REVISION
            or metadata.get("index_sha256") != hashlib.sha256(index_bytes).hexdigest()
            or not isinstance(metadata.get("documents"), list)
        ):
            raise ValueError(
                "Índice ou metadados incompatíveis. Reconstrua com semantic_search index."
            )
        self.index = faiss.deserialize_index(
            np.frombuffer(index_bytes, dtype=np.uint8).copy()
        )
        self.documents = metadata["documents"]
        if (
            self.index.ntotal != len(self.documents)
            or self.index.ntotal == 0
            or self.index.d != metadata.get("dimension")
            or self.index.metric_type != faiss.METRIC_INNER_PRODUCT
        ):
            raise ValueError("Índice e documentos inconsistentes. Reconstrua o índice.")
        self.encoder = encoder if encoder is not None else load_encoder()

    def search(self, query, top_k=3):
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A consulta não pode ser vazia.")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k deve ser um inteiro positivo.")
        vector = embed(self.encoder, [query])
        if vector.shape[1] != self.index.d:
            raise ValueError(
                "Dimensão do modelo difere do índice. Reconstrua o índice."
            )
        scores, positions = self.index.search(vector, min(top_k, self.index.ntotal))
        return [
            {
                "id": self.documents[position]["id"],
                "text": self.documents[position]["text"],
                "score": float(np.clip(score, -1.0, 1.0)),
            }
            for score, position in zip(scores[0], positions[0])
        ]
