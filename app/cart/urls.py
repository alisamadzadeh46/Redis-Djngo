from django.urls import path

from .views import AddToCartView

urlpatterns = [
    path("add/", AddToCartView.as_view()),
]
