import sqlite3
import json
from pathlib import Path

def inspect_db(db_path):
    print(f"=== Inspecting {db_path} ===")
    if not Path(db_path).exists():
        print("Does not exist")
        return
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    tables = cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
    for name, sql in tables:
        print(f"\nTable: {name}")
        print(f"SQL: {sql}")
        try:
            count = cur.execute(f"SELECT COUNT(*) FROM `{name}`").fetchone()[0]
            print(f"Row count: {count}")
            sample = cur.execute(f"SELECT * FROM `{name}` LIMIT 2").fetchall()
            cols = [d[0] for d in cur.description]
            print(f"Columns: {cols}")
        except Exception as e:
            print(f"Error querying table {name}: {e}")

inspect_db(r"B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db")
inspect_db(r"B:\ALL_TOOLS\CofiRadar\data\cofi_radar.db")
