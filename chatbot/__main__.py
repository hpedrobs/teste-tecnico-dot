"""Execute com python -m chatbot na raiz do projeto."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import APIError

from .service import ChatSession, create_chain, provider_error_message


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)
    tracing = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    if tracing and not os.getenv("LANGSMITH_API_KEY", "").strip():
        print("Erro: LANGSMITH_TRACING=true exige LANGSMITH_API_KEY.", file=sys.stderr)
        return 1
    try:
        session = ChatSession(create_chain(), tracing=tracing)
    except (ValueError, APIError) as error:
        message = (
            provider_error_message(error) if isinstance(error, APIError) else str(error)
        )
        print(f"Erro: {message}", file=sys.stderr)
        return 1
    print(
        "Tutor de Python. Digite 'sair' para encerrar. Histórico apenas nesta sessão."
    )
    if tracing:
        print(
            "LangSmith ativo: perguntas e respostas serão enviadas ao serviço de rastreamento."
        )
    while True:
        try:
            question = input("Você: ").strip()
            if question.casefold() in {"sair", "/sair"}:
                break
            if not question:
                continue
            try:
                print(f"Tutor: {session.ask(question)}")
            except APIError as error:
                print(f"Erro: {provider_error_message(error)}", file=sys.stderr)
            except ValueError as error:
                print(f"Erro: {error}", file=sys.stderr)
        except (EOFError, KeyboardInterrupt):
            break
    print("Conversa encerrada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
