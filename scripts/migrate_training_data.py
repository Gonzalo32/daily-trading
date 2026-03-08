import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1] / "daily-trading"
sys.path.insert(0, str(PROJECT_ROOT))

from src.ml.trade_recorder import TradeRecorder  # noqa: E402


def migrate(input_path: str, output_path: str) -> int:
    full_schema = list(TradeRecorder.FULL_SCHEMA)
    valid = 0
    repaired = 0
    discarded = 0

    if not os.path.exists(input_path):
        print(f"ERROR: input no existe: {input_path}")
        return 1

    with open(input_path, newline="", encoding="utf-8") as src, open(
        output_path, "w", newline="", encoding="utf-8"
    ) as dst:
        reader = csv.reader(src)
        writer = csv.writer(dst)
        header = next(reader, [])

        has_header = header and "timestamp" in header and "symbol" in header
        if has_header:
            header = [h.strip() for h in header]
        else:
            header = []

        writer.writerow(full_schema)

        for row in reader:
            if not row:
                discarded += 1
                continue

            if has_header:
                row_dict = {header[i]: row[i] for i in range(min(len(header), len(row)))}
                fixed_row = [row_dict.get(col, "") for col in full_schema]
                if len(row) != len(header):
                    repaired += 1
                else:
                    valid += 1
            else:
                if len(row) == len(full_schema):
                    fixed_row = row
                    valid += 1
                else:
                    fixed_row = (row + [""] * len(full_schema))[: len(full_schema)]
                    repaired += 1

            writer.writerow(fixed_row)

    print(f"OK: filas_validas={valid} | filas_reparadas={repaired} | filas_descartadas={discarded}")
    print(f"OK: output={output_path}")
    return 0


if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else "src/ml/training_data.csv"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "src/ml/training_data_v2.csv"
    raise SystemExit(migrate(input_file, output_file))
