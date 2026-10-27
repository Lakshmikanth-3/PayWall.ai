"""One-time Zetaris setup (idempotent): copy the catalog export into the Zetaris driver container and
register it as the file-store table paywall.catalog, then read it back through Zetaris SQL.
Usage (from backend/): python scripts/zetaris_setup.py   [env: ZETARIS_*, ZETARIS_DRIVER_CONTAINER]"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import zetaris
from app.config import settings

container = os.environ.get("ZETARIS_DRIVER_CONTAINER", "zetaris-driver-1")
path = "/home/zetaris/customer-data/shared/paywall"
db = settings.ZETARIS_SCHEMA
subprocess.run(["docker", "exec", container, "mkdir", "-p", path], check=True)
subprocess.run(["docker", "cp", os.path.join("data", "zetaris", "catalog.csv"), f"{container}:{path}/catalog.csv"], check=True)
for sql in (f'CREATE LIGHTNING DATABASE {db} DESCRIBE BY "PayWall.ai merchant catalog"',
            f'CREATE LIGHTNING FILESTORE TABLE catalog FROM {db} FORMAT CSV OPTIONS (path "{path}/catalog.csv", header "true", inferSchema "false")'):
    try:
        zetaris.run_sql(sql)
        print("ok:", sql.split(" FROM")[0][:60])
    except zetaris.ZetarisError as e:
        print("skipped (exists?):", str(e)[:120])
rows = zetaris.run_sql(f"SELECT product_id, product, amount, merchant_id FROM {db}.catalog")
print(f"read back {len(rows)} catalog rows through Zetaris")
