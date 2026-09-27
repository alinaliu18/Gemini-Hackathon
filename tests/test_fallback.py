"""Offline check of key/model fallback. Run: ./.venv/bin/python tests/test_fallback.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import backend
from pipeline import config

backend.CLIENTS = ["key1", "key2"]
calls = []

def fake(client, model):
    calls.append((client, model))
    if model == config.MODEL_ID:
        raise RuntimeError("503 UNAVAILABLE high demand")      # main model overloaded -> next model, skip other keys
    if client == "key1":
        raise RuntimeError("429 RESOURCE_EXHAUSTED")           # quota on key1 -> next key, same model
    return "ok"

assert backend.with_client(fake) == ("ok", config.FALLBACK_MODELS[0])
assert calls == [("key1", config.MODEL_ID), ("key1", config.FALLBACK_MODELS[0]), ("key2", config.FALLBACK_MODELS[0])]

try:
    backend.with_client(lambda c, m: (_ for _ in ()).throw(ValueError("bad request")))
    raise AssertionError("other errors must not be swallowed")
except ValueError:
    pass
calls.clear()
def retired(client, model):
    calls.append(model)
    if model != config.FALLBACK_MODELS[-1]:
        raise RuntimeError("404 NOT_FOUND model is no longer available")
    return "ok"
assert backend.with_client(retired) == ("ok", config.FALLBACK_MODELS[-1]) and len(set(calls)) == 1 + len(config.FALLBACK_MODELS)

print("ALL OK")
