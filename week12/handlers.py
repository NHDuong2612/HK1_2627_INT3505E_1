def v1_create_order(body):
    return {"account_id": body.get("account_id", ""), "version": "v1"}


def v2_create_order(body):
    return {"account_id": body.get("account_id", ""), "version": "v2"}
