from django.conf import settings
import redis
import json

redis_client = settings.REDIS_CLIENT

CART_TTL = 60 * 30  # 30 minutes


def _details_key(session_id):
    return f"{_cart_key(session_id)}:details"


def _cart_key(session_id):
    return f"cart:{session_id}"


def _refresh_cart_ttl_pipe(pipe, session_id):
    pipe.expire(_qty_key(session_id), CART_TTL)
    pipe.expire(_details_key(session_id), CART_TTL)
    pipe.expire(f"{_cart_key(session_id)}:promo_code", CART_TTL)


def _qty_key(session_id):
    return f"{_cart_key(session_id)}:qty"


def add_to_cart(session_id, product_id, quantity, name, price):
    qty_key = _qty_key(session_id)
    details_key = _details_key(session_id)
    pipe = redis_client.pipeline()
    pipe.hincrby(details_key, product_id, quantity)

    if not redis_client.hexists(details_key, product_id):
        product_data = {
            "product_id": product_id,
            "name": name,
            "price": float(price),

        }
        pipe.hset(details_key, product_id, json.dumps(product_data))
    _refresh_cart_ttl_pipe(pipe, session_id)
    pipe.execute()


def get_cart(session_id):
    qtys = redis_client.hgetall(_qty_key(session_id))
    details = redis_client.hgetall(_details_key(session_id))

    cart_items = []
    for pid, qty in qtys.items():
        detail_json = details.get(pid)
        if not detail_json:
            continue
        data = json.loads(detail_json)
        data['quantity'] = int(qty)
        cart_items.append(data)
    return cart_items


def remove_cart(session_id, product_id):
    qty_key = _qty_key(session_id)
    details_key = _details_key(session_id)
    promote_key = f"{_cart_key(session_id)}:promote"

    pipe = redis_client.pipeline()
    pipe.hdel(qty_key, product_id)
    pipe.hdel(details_key, product_id)

    if redis_client.hlen(qty_key) == 0:
        pipe.delete(promote_key)

    _refresh_cart_ttl_pipe(pipe, session_id)
    pipe.execute()


def clear_cart(session_id):
    pipe = redis_client.pipeline()
    pipe.delete(_qty_key(session_id))
    pipe.delete(_details_key(session_id))
    pipe.delete(f"{_cart_key(session_id)}:promo_code")
    pipe.execute()


def get_cart_promo_code(session_id):
    key = f"cart:{session_id}:promo_code"
    return redis_client.get(key)


def increment_quantity(session_id, product_id, step=1):
    pipe = redis_client.pipeline()
    pipe.hincrby(_qty_key(session_id), product_id, step)
    _refresh_cart_ttl_pipe(pipe, session_id)
    pipe.execute()
    return True


def decrement_quantity(session_id, product_id, step=1):
    qty_key = _qty_key(session_id)
    details_key = _details_key(session_id)
    new_qty = redis_client.hincrby(qty_key, product_id, -step)
    if new_qty < 1:
        pipe = redis_client.pipeline()
        redis_client.hdel(qty_key, product_id)
        redis_client.hdel(_details_key, product_id)
        _refresh_cart_ttl_pipe(pipe,session_id)
        pipe.execute()
    else:
        pipe = redis_client.pipeline()
        _refresh_cart_ttl_pipe(pipe, session_id)
        pipe.execute()
    return True


def set_quantity(session_id, product_id, quantity):
    key = _cart_key(session_id)
    existing = redis_client.hget(key, product_id)

    if not existing:
        return False

    data = json.loads(existing)
    data["quantity"] = quantity
    redis_client.hset(key, product_id, json.dumps(data))

    pipe = redis_client.pipeline()
    _refresh_cart_ttl_pipe(pipe, session_id)
    pipe.execute()

    return True


def set_cart_promo_code(session_id, promo_code):
    pipe = redis_client.pipeline()
    pipe.set(f"{_cart_key(session_id)}:promo_code", promo_code)
    _refresh_cart_ttl_pipe(pipe, session_id)
    pipe.execute()


def update_cart_item(session_id, product_id, name, price, quantity):
    pipe = redis_client.pipeline()
    details = {
        "product_id": product_id,
        "name": name,
        "price": float(price),
    }

    redis_client.hset(_details_key(session_id), product_id, json.dumps(details))
    redis_client.hset(_qty_key(session_id), product_id, quantity)
    _refresh_cart_ttl_pipe(pipe,session_id)
    pipe.execute()


def remove_from_cart(session_id, product_id):
    redis_client.hdel(_qty_key(session_id), product_id)
    redis_client.hdel(_details_key(session_id), product_id)

    if redis_client.hlen(_qty_key(session_id)) == 0:
        redis_client.delete(f"{_cart_key(session_id)}:promo_code")

        _refresh_cart_ttl(session_id)
