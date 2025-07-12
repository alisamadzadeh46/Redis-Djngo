from django.urls import path

from .views import *

urlpatterns = [
    path("add/", AddToCartView.as_view()),
    path("get/", CartView.as_view()),
    path("delete/", RemoveFromCartView.as_view()),
    path("increment/", UpdateQuantityView.as_view()),
    path("update/qty/", SetQuantityView.as_view()),
    path("promo/", CartPromoView.as_view()),
    path("checkout/", CartCheckoutView.as_view()),

]
