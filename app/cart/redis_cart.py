from django.conf import settings
import redis
import json

redis_client = settings.REDIS_CLIENT


def _cart_key(session_id):
    return f"cart:{session_id}"


def add_to_cart(session_id, product_id, quantity, name, price):
    cart_key = _cart_key(session_id)
    product_data = {
        "product_id": product_id,
        "name": name,
        "price": float(price),
        "quantity": int(quantity),

    }

    redis_client.hset(cart_key, product_id, json.dumps(product_data))


def get_cart(session_id):
    key = _cart_key(session_id)
    raw_cart = redis_client.hgetall(key)
    return [json.loads(item) for item in raw_cart.values()]


def remove_cart(session_id, product_id):
    key = _cart_key(session_id)
    redis_client.hdel(key,product_id)
