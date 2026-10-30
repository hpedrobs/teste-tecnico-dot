from django.urls import path

from .views import BookListCreateView

urlpatterns = [path("livros/", BookListCreateView.as_view(), name="book-list-create")]
