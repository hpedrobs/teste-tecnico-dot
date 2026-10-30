"""Prompt, integração oficial OpenAI e memória volátil de uma sessão."""

import os

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langsmith import tracing_context
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

SYSTEM_PROMPT = (
    "Você é um tutor didático de programação Python. Responda em português. "
    "Explique os conceitos passo a passo, com exemplos pequenos de código e "
    "o resultado esperado quando útil. Considere as perguntas anteriores. "
    "Se faltar contexto, peça esclarecimento. Se não souber, diga isso. "
    "Para assuntos fora de Python, oriente gentilmente a conversa para Python. "
    "Não afirme que executou código; os exemplos são ilustrativos."
)


def create_chain():
    key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip()
    if not key or not model:
        raise ValueError(
            "Configure OPENAI_API_KEY e OPENAI_MODEL no ambiente ou no arquivo .env."
        )
    llm = ChatOpenAI(model=model, api_key=key, timeout=30, max_retries=1)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]
    )
    # LCEL compõe o prompt, o modelo e o parser sem chains legadas.
    return prompt | llm | StrOutputParser()


class ChatSession:
    def __init__(self, chain, *, tracing=False):
        self.chain = chain
        self.tracing = tracing
        self.history = []

    def ask(self, question):
        question = question.strip()
        if not question:
            raise ValueError("Digite uma pergunta sobre Python.")
        # Desativa traces explicitamente por padrão, inclusive se houver uma
        # variável legada LANGCHAIN_TRACING_V2 no ambiente da máquina.
        with tracing_context(enabled=self.tracing):
            answer = self.chain.invoke(
                {"history": list(self.history), "question": question}
            )
        if not answer.strip():
            raise ValueError(
                "O modelo não retornou texto. Confira se o modelo aceita conversas em texto."
            )
        # Só confirma o turno após sucesso: falhas não contaminam a conversa.
        self.history.extend([HumanMessage(content=question), AIMessage(content=answer)])
        return answer


def provider_error_message(error: APIError):
    """Não expõe a resposta bruta do provedor, headers nem credenciais."""
    if isinstance(error, AuthenticationError):
        return "Credencial recusada pela OpenAI. Confira OPENAI_API_KEY."
    if isinstance(error, (NotFoundError, PermissionDeniedError)):
        return "Modelo indisponível ou sem permissão. Confira OPENAI_MODEL e o acesso da sua conta."
    if isinstance(error, RateLimitError):
        return "Limite de uso ou cota atingidos. Confira saldo e limites na OpenAI e tente depois."
    if isinstance(error, (APITimeoutError, APIConnectionError)):
        return "Não foi possível conectar à OpenAI no prazo. Confira a rede e tente novamente."
    if isinstance(error, BadRequestError):
        return "A OpenAI recusou a solicitação. Confira a compatibilidade do modelo; se a sessão estiver longa, reinicie."
    return "Falha temporária da OpenAI. Tente novamente mais tarde."
