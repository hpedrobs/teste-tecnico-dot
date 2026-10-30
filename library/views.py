import re

from rest_framework.generics import ListCreateAPIView

from .models import Book
from .serializers import BookSerializer


class BookListCreateView(ListCreateAPIView):
    """GET lista/filtra livros; POST valida e persiste um livro."""

    serializer_class = BookSerializer

    def get_queryset(self):
        books = Book.objects.all()
        for field in ("titulo", "autor"):
            value = self.request.query_params.get(field, "").strip()
            if value:
                # SQLite não faz icontains Unicode completo. O backend Django
                # executa iregex com re do Python, incluindo letras acentuadas.
                # escape torna a entrada literal; o usuário não controla regex.
                books = books.filter(**{f"{field}__iregex": re.escape(value)})
        # Filtros sucessivos representam interseção (E).
        return books
