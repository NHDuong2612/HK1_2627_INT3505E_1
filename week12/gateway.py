import hashlib

from flask import request

from handlers import v1_create_order, v2_create_order


V2_PERCENT = 100
V2_COHORTS = {"beta", "internal"}
V2_FORCE_ACCOUNTS = {"acct_42", "acct_99"}


def route_to_v2(body):
    cohort = request.headers.get("X-Cohort", "").lower()
    if cohort in V2_COHORTS:
        return True

    account_id = body.get("account_id", "")
    if account_id in V2_FORCE_ACCOUNTS:
        return True

    if V2_PERCENT == 0:
        return False
    bucket = int(hashlib.md5(account_id.encode()).hexdigest(), 16) % 100
    return bucket < V2_PERCENT


def dispatch(body):
    if route_to_v2(body):
        return "v2", v2_create_order(body)
    return "v1", v1_create_order(body)
