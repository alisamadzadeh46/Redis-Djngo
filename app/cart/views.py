from django.shortcuts import render
from .serializers import *
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from . import redis_cart
from inventory.models import Product
from rest_framework import status
from rest_framework.response import Response


class CartView(APIView):
    @extend_schema(
        responses={200: CartItemSerializer(many=True)},
        description="Get all cart items for the current session.",
    )
    def get(self, request):
        session_id = request.session.session_key
        cart_data = redis_cart.get_cart(session_id)
        promo_code = redis_cart.get_cart_promo_code(session_id)
        return Response(
            {"items": cart_data, "promo_code": promo_code},
        )

    def delete(self, request):
        session_id = request.session.session_key
        redis_cart.clear_cart(session_id)
        return Response({"message": "Cart cleared."}, status=status.HTTP_200_OK)


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


class RemoveFromCartView(APIView):
    @extend_schema(
        request=RemoveFromCartSerializer,
        responses={200: None},
        description="Remove a product from the current cart session.",
    )
    def post(self, request):
        session_id = request.session.session_key

        serializer = RemoveFromCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data["product_id"]

        redis_cart.remove_cart(session_id, product_id)

        return Response({"message": "Removed from cart."})


class UpdateQuantityView(APIView):
    @extend_schema(
        request=UpdateQuantitySerializer,
        responses={200: None},
        description="Update quantity of a product in the cart. Action can be 'inc' or 'dec'.",
    )
    def post(self, request):
        session_id = request.session.session_key
        product_id = request.data.get("product_id")
        action = request.data.get("action", "inc")  # "inc" or "dec"

        if action == "inc":
            redis_cart.increment_quantity(session_id, product_id)
        else:
            redis_cart.decrement_quantity(session_id, product_id)

        return Response({"message": f"{action} quantity successful"})


class SetQuantityView(APIView):
    @extend_schema(
        request=SetQuantitySerializer,
        responses={200: None},
        description="Set a specific quantity for a product in the cart.",
    )
    def post(self, request):
        session_id = request.session.session_key or request.session.create()

        serializer = SetQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]

        updated = redis_cart.set_quantity(session_id, product_id, quantity)

        if not updated:
            return Response({"error": "Product not found in cart."}, status=404)

        return Response({"message": f"Quantity updated to {quantity}"})


class CartPromoView(APIView):
    @extend_schema(
        request=CartPromoSerializer,
        responses={200: None},
        description="Apply a promo code to the cart.",
    )
    def post(self, request):
        session_id = request.session.session_key

        serializer = CartPromoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        promo_code = serializer.validated_data["promo_code"]
        redis_cart.set_cart_promo_code(session_id, promo_code)

        return Response({"message": "Cart promotion code set."})

class CartCheckoutView(APIView):
    @extend_schema(
        responses={200: CheckoutResponseItemSerializer(many=True)},
        description="Validate and sanitize the cart before checkout. Removes missing products and updates price/name if needed.",
    )
    def post(self, request):
        session_id = request.session.session_key
        cart_items = redis_cart.get_cart(session_id)

        if not cart_items:
            return Response([])

        product_ids = [item["product_id"] for item in cart_items]

        # ✅ Single DB hit: get all products that are still active
        products = Product.objects.filter(id__in=product_ids, is_active=True)
        product_map = {product.id: product for product in products}

        cleaned_cart = []

        for item in cart_items:
            product_id = item["product_id"]
            product = product_map.get(product_id)

            if not product:
                redis_cart.remove_from_cart(session_id, product_id)
                continue

            # Check if Redis-stored name/price differs
            if item["name"] != product.name or float(item["price"]) != float(
                product.price
            ):
                redis_cart.update_cart_item(
                    session_id,
                    product_id,
                    product.name,
                    product.price,
                    item["quantity"],
                )
                item["name"] = product.name
                item["price"] = float(product.price)

            item["valid"] = True
            item["error"] = ""
            cleaned_cart.append(item)

        return Response(cleaned_cart)
