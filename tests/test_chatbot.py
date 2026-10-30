import io
import os
from unittest import TestCase
from unittest.mock import patch

import httpx
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from chatbot.__main__ import main
from chatbot.service import ChatSession, create_chain, provider_error_message


class ChatbotTests(TestCase):
    @patch.dict(os.environ, {"OPENAI_API_KEY": "", "OPENAI_MODEL": ""}, clear=True)
    def test_missing_credentials(self):
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY e OPENAI_MODEL"):
            create_chain()

    @patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "placeholder-for-mock", "OPENAI_MODEL": "test-model"},
        clear=True,
    )
    def test_real_prompt_and_parser_keep_session_context(self):
        received = []

        def fake_model(prompt):
            received.append(prompt.to_messages())
            return AIMessage(
                content="Use frutas = ['maçã']."
                if len(received) == 1
                else "Use frutas.append('uva')."
            )

        with patch(
            "chatbot.service.ChatOpenAI", return_value=RunnableLambda(fake_model)
        ) as model:
            session = ChatSession(create_chain())
            self.assertIn("frutas", session.ask("Como criar uma lista em Python?"))
            self.assertIn("append", session.ask("E como acrescentar um item nela?"))
        self.assertIn("português", received[0][0].content)
        self.assertEqual(
            [message.type for message in received[1]],
            ["system", "human", "ai", "human"],
        )
        self.assertEqual(received[1][1].content, "Como criar uma lista em Python?")
        self.assertEqual(len(session.history), 4)
        model.assert_called_once_with(
            model="test-model",
            api_key="placeholder-for-mock",
            timeout=30,
            max_retries=1,
        )

    def test_failure_does_not_change_history(self):
        def fail(_):
            raise APIConnectionError(
                request=httpx.Request("POST", "https://api.openai.com")
            )

        session = ChatSession(RunnableLambda(fail))
        with self.assertRaises(APIConnectionError):
            session.ask("Como criar uma lista?")
        self.assertEqual(session.history, [])

    def test_sessions_are_isolated(self):
        chain = RunnableLambda(lambda _: "Exemplo ilustrativo.")
        first, second = ChatSession(chain), ChatSession(chain)
        first.ask("Como criar uma lista?")
        self.assertEqual(second.history, [])

    def test_empty_question_and_empty_response(self):
        session = ChatSession(RunnableLambda(lambda _: " "))
        with self.assertRaisesRegex(ValueError, "Digite"):
            session.ask(" ")
        with self.assertRaisesRegex(ValueError, "não retornou texto"):
            session.ask("Uma pergunta")
        self.assertEqual(session.history, [])

    def test_provider_errors_are_clear_and_do_not_expose_response(self):
        request = httpx.Request("POST", "https://api.openai.com")
        for cls, status, expected in (
            (AuthenticationError, 401, "Credencial"),
            (NotFoundError, 404, "Modelo"),
            (PermissionDeniedError, 403, "Modelo"),
            (RateLimitError, 429, "cota"),
            (BadRequestError, 400, "compatibilidade"),
            (APIStatusError, 500, "temporária"),
        ):
            with self.subTest(cls=cls):
                error = cls(
                    "provider-private-details",
                    response=httpx.Response(status, request=request),
                    body=None,
                )
                message = provider_error_message(error)
                self.assertIn(expected, message)
                self.assertNotIn("provider-private-details", message)
        for cls in (APIConnectionError, APITimeoutError):
            self.assertIn("rede", provider_error_message(cls(request=request)))

    @patch.dict(os.environ, {}, clear=True)
    @patch("chatbot.__main__.load_dotenv")
    @patch("chatbot.__main__.create_chain")
    def test_terminal_context_blank_input_and_exit(self, factory, _dotenv):
        questions = []
        factory.return_value = RunnableLambda(
            lambda values: questions.append(values) or "Resposta didática."
        )
        with (
            patch(
                "builtins.input",
                side_effect=[" ", "Como criar uma lista?", "E adicionar?", "SAIR"],
            ),
            patch("sys.stdout", new_callable=io.StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(len(questions), 2)
        self.assertEqual(len(questions[1]["history"]), 2)
        self.assertIn("Conversa encerrada", output.getvalue())

    @patch.dict(os.environ, {}, clear=True)
    @patch("chatbot.__main__.load_dotenv")
    def test_terminal_missing_credentials(self, _dotenv):
        with patch("sys.stderr", new_callable=io.StringIO) as error:
            self.assertEqual(main(), 1)
        self.assertIn("OPENAI_MODEL", error.getvalue())

    @patch.dict(os.environ, {"LANGSMITH_TRACING": "true"}, clear=True)
    @patch("chatbot.__main__.load_dotenv")
    def test_optional_tracing_requires_key(self, _dotenv):
        with patch("sys.stderr", new_callable=io.StringIO) as error:
            self.assertEqual(main(), 1)
        self.assertIn("LANGSMITH_API_KEY", error.getvalue())

    def test_tracing_disabled_by_default(self):
        with patch("chatbot.service.tracing_context") as tracing:
            ChatSession(RunnableLambda(lambda _: "Resposta")).ask("Python?")
        tracing.assert_called_once_with(enabled=False)

    @patch.dict(os.environ, {}, clear=True)
    @patch("chatbot.__main__.load_dotenv")
    @patch("chatbot.__main__.create_chain")
    def test_terminal_continues_after_provider_failure(self, factory, _dotenv):
        calls = []

        def model(values):
            calls.append(values)
            if len(calls) == 1:
                raise APIConnectionError(
                    request=httpx.Request("POST", "https://api.openai.com")
                )
            return "Use uma lista."

        factory.return_value = RunnableLambda(model)
        with (
            patch(
                "builtins.input", side_effect=["Pergunta", "Tentar novamente", EOFError]
            ),
            patch("sys.stdout", new_callable=io.StringIO),
            patch("sys.stderr", new_callable=io.StringIO) as error,
        ):
            self.assertEqual(main(), 0)
        self.assertIn("rede", error.getvalue())
        self.assertEqual(calls[1]["history"], [])
