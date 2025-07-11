from django.conf import settings
import redis
import json

redis_client = settings.REDIS_CLIENT


def _cart_ky(session_id):
    return f"cart:{session_id}"


def add_to_cart(session_id, product_id, quantity, name, price):
    cart_key = _cart_ky(session_id)
    product_data = {
        "product_id": product_id,
        "name": name,
        "price": float(price),
        "quantity": int(quantity),

    }

    redis_client.hset(cart_key, product_id ,json.dumps(product_data))
