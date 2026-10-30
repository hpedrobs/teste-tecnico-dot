from rest_framework import serializers

from .models import Book


class BookSerializer(serializers.ModelSerializer):
    # ISO explícito evita aceitar formatos dependentes da configuração regional.
    data_publicacao = serializers.DateField(input_formats=["%Y-%m-%d"])

    class Meta:
        model = Book
        fields = ["id", "titulo", "autor", "data_publicacao", "resumo"]
        read_only_fields = ["id"]
