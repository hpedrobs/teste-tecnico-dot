import argparse
import json
import sys
from pathlib import Path

from .service import DEFAULT_DOCUMENTS, DEFAULT_INDEX_DIR, SemanticSearch, build_index


def main():
    parser = argparse.ArgumentParser(
        description="Busca semântica local sobre programação Python."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    index_parser = commands.add_parser(
        "index", help="Gera/reconstrói os embeddings dos documentos."
    )
    index_parser.add_argument("--documents", type=Path, default=DEFAULT_DOCUMENTS)
    index_parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    search_parser = commands.add_parser("search", help="Consulta um índice existente.")
    search_parser.add_argument("query", help="Pergunta ou texto de consulta.")
    search_parser.add_argument("--top-k", type=int, default=3)
    search_parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    args = parser.parse_args()
    try:
        if args.command == "index":
            count = build_index(args.documents, args.index_dir)
            print(f"Índice criado com {count} documentos em {args.index_dir}.")
        else:
            # Valida antes de carregar o modelo/download.
            if not args.query.strip() or args.top_k < 1:
                parser.error("informe uma consulta não vazia e --top-k positivo")
            results = SemanticSearch(args.index_dir).search(args.query, args.top_k)
            print(json.dumps(results, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Erro na busca semântica: {error}", file=sys.stderr)
        print(
            "Confira os documentos, a rede no download inicial e reconstrua o índice se necessário.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
