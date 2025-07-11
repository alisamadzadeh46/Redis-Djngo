from django.shortcuts import render
from .serializers import *
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from . import redis_cart
from rest_framework import status
from rest_framework.response import Response

class AddToCartView(APIView):
    @extend_schema(
        request=AddToCartSerializer,
        responses={200: None},
        description="Add a product to the cart. Product data is sent from client.",
    )
    def post(self, request):
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key

        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        redis_cart.add_to_cart(
            session_id,
            product_id=data["product_id"],
            quantity=data["quantity"],
            name=data["name"],
            price=data["price"],
        )

        return Response({"message": "Added to cart."}, status=status.HTTP_200_OK)
