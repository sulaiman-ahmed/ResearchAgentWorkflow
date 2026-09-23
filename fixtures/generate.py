"""
Generate all demo fixtures deterministically.

Run from the repo root:
    uv run python fixtures/generate.py

Writes all CSV inputs and JSON expected outputs into fixtures/.
Produces the same output on every run — no randomness.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------

TARGETS = ["PROT_A", "PROT_B", "PROT_C"]
ASSAY_TYPES = ["binding", "viability", "inhibition"]
UNITS = ["nM", "uM", "%", "RLU"]
CANONICAL_UNIT_MAP = {"nM": "nM", "uM": "uM", "%": "%", "RLU": "RLU"}

# 30 synthetic samples: SAMP_001 … SAMP_030
# Sample SAMP_025 and SAMP_026 both carry alias "AMB_ALIAS" → ambiguous match
SAMPLES: list[dict] = []
for i in range(1, 31):
    code = f"SAMP_{i:03d}"
    aliases = [f"{code}_alias"]
    if code in ("SAMP_025", "SAMP_026"):
        aliases.append("AMB_ALIAS")
    SAMPLES.append(
        {
            "id": f"sample-{i:03d}",
            "canonical_code": code,
            "label": f"Sample {i}",
            "aliases": aliases,
        }
    )

# 5 synthetic molecules
MOLECULES: list[dict] = [
    {
        "id": "mol-001",
        "name": "SynthMol-Alpha",
        "aliases": ["SMA", "compound-1"],
        "target_id": "PROT_A",
        "is_synthetic": True,
        "properties": {"mw": 342.4, "solubility": "high"},
    },
    {
        "id": "mol-002",
        "name": "SynthMol-Beta",
        "aliases": ["SMB"],
        "target_id": "PROT_A",
        "is_synthetic": True,
        "properties": {"mw": 418.2, "solubility": "moderate"},
    },
    {
        "id": "mol-003",
        "name": "SynthMol-Gamma",
        "aliases": ["SMG", "compound-3"],
        "target_id": "PROT_B",
        "is_synthetic": True,
        "properties": {"mw": 289.1, "solubility": "low"},
    },
    {
        "id": "mol-004",
        "name": "SynthMol-Delta",
        "aliases": ["SMD"],
        "target_id": "PROT_B",
        "is_synthetic": True,
        "properties": {"mw": 501.7, "solubility": "high"},
    },
    {
        "id": "mol-005",
        "name": "SynthMol-Epsilon",
        "aliases": ["SME"],
        "target_id": "PROT_C",
        "is_synthetic": True,
        "properties": {"mw": 377.9, "solubility": "moderate"},
    },
]

# 20 historical experiments with explicit outcomes
# Experiments 1–10: PROT_A / binding
# Experiments 11–15: PROT_B / viability
# Experiments 16–20: PROT_C / inhibition
_CONDITIONS_BY_IDX = [
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 50},
    {"ph": 6.8, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 37, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.2, "temperature_c": 25, "concentration_uM": 100},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 30, "concentration_uM": 25},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.0, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 37, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 37, "concentration_uM": 50},
    {"ph": 7.4, "temperature_c": 37, "concentration_uM": 10},
    {"ph": 6.8, "temperature_c": 37, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 37, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 20},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.2, "temperature_c": 25, "concentration_uM": 10},
    {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
]

_OUTCOMES = [
    # PROT_A / binding (indices 0–9)
    ("success", None),
    ("failure", "reagent_preparation"),
    ("success", None),
    ("failure", "instrument_calibration"),
    ("success", None),
    ("success", None),
    ("failure", "sample_degradation"),
    ("success", None),
    ("success", None),
    ("success", None),
    # PROT_B / viability (indices 10–14)
    ("success", None),
    ("failure", "cell_viability_threshold"),
    ("success", None),
    ("success", None),
    ("failure", "reagent_preparation"),
    # PROT_C / inhibition (indices 15–19)
    ("success", None),
    ("success", None),
    ("failure", "instrument_calibration"),
    ("success", None),
    ("success", None),
]

EXPERIMENTS: list[dict] = []
for i in range(20):
    idx = i + 1
    if i < 10:
        target, assay = "PROT_A", "binding"
    elif i < 15:
        target, assay = "PROT_B", "viability"
    else:
        target, assay = "PROT_C", "inhibition"
    outcome, failure_step = _OUTCOMES[i]
    EXPERIMENTS.append(
        {
            "id": f"exp-{idx:03d}",
            "name": f"Experiment {idx:02d}",
            "target_id": target,
            "assay_type": assay,
            "conditions": _CONDITIONS_BY_IDX[i],
            "status": "completed",
            "recorded_outcome": outcome,
            "failure_step": failure_step,
            "version": 1,
        }
    )

# ---------------------------------------------------------------------------
# 20 clean measurement rows (canonical sample codes SAMP_001–SAMP_020)
# ---------------------------------------------------------------------------

_CLEAN_ROWS: list[dict] = [
    {
        "sample_id": f"SAMP_{i:03d}",
        "measurement_name": "binding_affinity",
        "value": str(round(10.0 + i * 1.5, 1)),
        "unit": "nM",
    }
    for i in range(1, 21)
]

# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: object) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Fixture 1: clean.csv  — 20 valid rows, canonical headers
# ---------------------------------------------------------------------------


def make_clean() -> None:
    _write_csv(
        FIXTURES_DIR / "clean.csv",
        ["sample_id", "measurement_name", "value", "unit"],
        _CLEAN_ROWS,
    )
    expected = {
        "status": "ok",
        "record_count": 20,
        "issues": [],
        "rows": _CLEAN_ROWS,
    }
    _write_json(FIXTURES_DIR / "clean.expected.json", expected)


# ---------------------------------------------------------------------------
# Fixture 2: renamed_headers.csv  — same 20 values, non-canonical headers
# ---------------------------------------------------------------------------


def make_renamed_headers() -> None:
    renamed_rows = [
        {
            "sampleID": r["sample_id"],
            "assay": r["measurement_name"],
            "result": r["value"],
            "units": r["unit"],
        }
        for r in _CLEAN_ROWS
    ]
    _write_csv(
        FIXTURES_DIR / "renamed_headers.csv",
        ["sampleID", "assay", "result", "units"],
        renamed_rows,
    )
    expected = {
        "status": "ok",
        "record_count": 20,
        "issues": [],
        "header_mapping": {
            "sampleID": "sample_id",
            "assay": "measurement_name",
            "result": "value",
            "units": "unit",
        },
        "rows": _CLEAN_ROWS,
    }
    _write_json(FIXTURES_DIR / "renamed_headers.expected.json", expected)


# ---------------------------------------------------------------------------
# Fixture 3: unknown_sample.csv  — 20 valid + 1 unknown sample
# ---------------------------------------------------------------------------


def make_unknown_sample() -> None:
    rows = list(_CLEAN_ROWS) + [
        {
            "sample_id": "SAMP_UNKNOWN_999",
            "measurement_name": "binding_affinity",
            "value": "99.9",
            "unit": "nM",
        }
    ]
    _write_csv(
        FIXTURES_DIR / "unknown_sample.csv",
        ["sample_id", "measurement_name", "value", "unit"],
        rows,
    )
    expected = {
        "status": "has_issues",
        "record_count": 21,
        "issues": [
            {
                "record_index": 20,
                "field": "sample_id",
                "kind": "unknown_sample",
                "value": "SAMP_UNKNOWN_999",
                "message": "No sample found for identifier 'SAMP_UNKNOWN_999'",
            }
        ],
        "valid_record_count": 20,
    }
    _write_json(FIXTURES_DIR / "unknown_sample.expected.json", expected)


# ---------------------------------------------------------------------------
# Fixture 4: ambiguous_alias.csv  — 20 valid + 1 ambiguous alias
# ---------------------------------------------------------------------------


def make_ambiguous_alias() -> None:
    rows = list(_CLEAN_ROWS) + [
        {
            "sample_id": "AMB_ALIAS",
            "measurement_name": "binding_affinity",
            "value": "55.0",
            "unit": "nM",
        }
    ]
    _write_csv(
        FIXTURES_DIR / "ambiguous_alias.csv",
        ["sample_id", "measurement_name", "value", "unit"],
        rows,
    )
    expected = {
        "status": "has_issues",
        "record_count": 21,
        "issues": [
            {
                "record_index": 20,
                "field": "sample_id",
                "kind": "ambiguous_alias",
                "value": "AMB_ALIAS",
                "matched_canonical_codes": ["SAMP_025", "SAMP_026"],
                "message": "Alias 'AMB_ALIAS' matches multiple samples: SAMP_025, SAMP_026",
            }
        ],
        "valid_record_count": 20,
    }
    _write_json(FIXTURES_DIR / "ambiguous_alias.expected.json", expected)


# ---------------------------------------------------------------------------
# Fixture 5: bad_unit.csv  — 20 valid + 1 unsupported unit
# ---------------------------------------------------------------------------


def make_bad_unit() -> None:
    rows = list(_CLEAN_ROWS) + [
        {
            "sample_id": "SAMP_001",
            "measurement_name": "binding_affinity",
            "value": "12.5",
            "unit": "moles_per_furlong",
        }
    ]
    _write_csv(
        FIXTURES_DIR / "bad_unit.csv",
        ["sample_id", "measurement_name", "value", "unit"],
        rows,
    )
    expected = {
        "status": "has_issues",
        "record_count": 21,
        "issues": [
            {
                "record_index": 20,
                "field": "unit",
                "kind": "unsupported_unit",
                "value": "moles_per_furlong",
                "message": "Unit 'moles_per_furlong' is not in the supported unit list",
            }
        ],
        "valid_record_count": 20,
    }
    _write_json(FIXTURES_DIR / "bad_unit.expected.json", expected)


# ---------------------------------------------------------------------------
# Fixture 6: malformed.csv  — file-level parse failure (unclosed quote)
# ---------------------------------------------------------------------------


def make_malformed() -> None:
    content = 'sample_id,measurement_name,value,unit\nSAMP_001,"binding_affinity,10.0,nM\n'
    (FIXTURES_DIR / "malformed.csv").write_text(content, encoding="utf-8")
    expected = {
        "status": "parse_error",
        "record_count": 0,
        "issues": [
            {
                "record_index": None,
                "field": None,
                "kind": "parse_error",
                "message": "File could not be parsed as valid CSV",
            }
        ],
    }
    _write_json(FIXTURES_DIR / "malformed.expected.json", expected)


# ---------------------------------------------------------------------------
# Historical check cases
# ---------------------------------------------------------------------------


def make_historical_check_cases() -> None:
    # Case 1: new PROT_A / binding experiment — 3 comparable experiments exist,
    # 2 of which are failures (exp-002: reagent_preparation, exp-004: instrument_calibration)
    case_with_history = {
        "description": "New PROT_A binding experiment with comparable history",
        "new_experiment": {
            "id": "exp-NEW-001",
            "target_id": "PROT_A",
            "assay_type": "binding",
            "conditions": {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
        },
        "expected": {
            "status": "has_history",
            "comparable_experiment_ids": ["exp-001", "exp-003", "exp-005"],
            "candidate_count": 3,
            "failure_count": 2,
            "failure_steps": ["reagent_preparation", "instrument_calibration"],
            "abstained": False,
        },
    }

    # Case 2: new PROT_C / binding experiment — no comparable history
    case_no_history = {
        "description": "New PROT_C binding experiment with no comparable history",
        "new_experiment": {
            "id": "exp-NEW-002",
            "target_id": "PROT_C",
            "assay_type": "binding",
            "conditions": {"ph": 7.4, "temperature_c": 25, "concentration_uM": 10},
        },
        "expected": {
            "status": "no_history",
            "comparable_experiment_ids": [],
            "candidate_count": 0,
            "failure_count": 0,
            "failure_steps": [],
            "abstained": True,
        },
    }

    _write_json(
        FIXTURES_DIR / "historical_check_with_history.json",
        case_with_history,
    )
    _write_json(
        FIXTURES_DIR / "historical_check_no_history.json",
        case_no_history,
    )


# ---------------------------------------------------------------------------
# Master data snapshots (used by seed_demo in Issue 06)
# ---------------------------------------------------------------------------


def make_master_data() -> None:
    _write_json(FIXTURES_DIR / "samples.json", SAMPLES)
    _write_json(FIXTURES_DIR / "molecules.json", MOLECULES)
    _write_json(FIXTURES_DIR / "experiments.json", EXPERIMENTS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    FIXTURES_DIR.mkdir(exist_ok=True)

    make_clean()
    make_renamed_headers()
    make_unknown_sample()
    make_ambiguous_alias()
    make_bad_unit()
    make_malformed()
    make_historical_check_cases()
    make_master_data()

    print("Fixtures written to fixtures/:")
    for p in sorted(FIXTURES_DIR.glob("*")):
        if p.is_file() and p.name != "generate.py":
            print(f"  {p.name}")


if __name__ == "__main__":
    main()
