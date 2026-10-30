from django.db import models


class Book(models.Model):
    titulo = models.CharField(max_length=255)
    autor = models.CharField(max_length=255)
    data_publicacao = models.DateField()
    resumo = models.TextField(max_length=10000)

    class Meta:
        ordering = ["id"]
