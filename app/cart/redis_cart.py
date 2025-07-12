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
    redis_client.hdel(key, product_id)


def clear_cart(session_id):
    key = _cart_key(session_id)
    redis_client.delete(key)


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

    MAX_ATTEMPTS = 5

    for attempt in range(MAX_ATTEMPTS):
        try:
            with redis_client.pipeline() as pipe:
                pipe.watch(qty_key)

                # Use direct client method (not through pipe)
                current_qty = redis_client.hget(qty_key, product_id)
                if current_qty is None:
                    pipe.unwatch()
                    return False

                current_qty = int(current_qty)
                new_qty = current_qty - step

                pipe.multi()

                if new_qty < 1:
                    pipe.hdel(qty_key, product_id)
                    pipe.hdel(details_key, product_id)
                else:
                    pipe.hset(qty_key, product_id, new_qty)

                _refresh_cart_ttl_pipe(pipe, session_id)
                pipe.execute()
                return True

        except redis_client.WatchError:
            continue


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
