"""Explicit, non-HTTP Lambda handler for the one-time Alembic migration."""

from api.runtime_config import load_ssm_parameters

load_ssm_parameters()

from alembic import command
from alembic.config import Config


def handler(event, context):
    if event.get("confirm") != "upgrade-head":
        raise ValueError("Migration requires confirm=upgrade-head")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    return {"status": "ok", "revision": "head"}
