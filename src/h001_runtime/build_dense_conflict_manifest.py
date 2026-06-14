import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.dense_conflict_manifest_builder.v1"
SPLIT_SCHEMA_VERSION = "h001.split_manifest.v1"
DEFAULT_SELECTED_SPLIT = "dense_conflict_v1"
DEFAULT_SEED = 20260521

PRIMARY_TARGETS = [
    {
        "episode_key": "HM3D ObjectNav v2:val:DYehNKdT76V:22:4:chair",
        "role": "primary",
        "conflict_class": "correct_and_wrong_positive_unresolved",
    },
    {
        "episode_key": "HM3D ObjectNav v2:val:HY1NcmCgn3n:1:1:plant",
        "role": "primary",
        "conflict_class": "correct_and_wrong_positive_selected_correct",
    },
    {
        "episode_key": "HM3D ObjectNav v2:val:7MXmsvcQjpJ:26:0:plant",
        "role": "primary",
        "conflict_class": "selected_wrong_positive_correct_present",
    },
    {
        "episode_key": "HM3D ObjectNav v2:val:HY1NcmCgn3n:8:8:plant",
        "role": "primary",
        "conflict_class": "correct_and_wrong_positive_selected_correct",
    },
    {
        "episode_key": "HM3D ObjectNav v2:val:7MXmsvcQjpJ:5:2:plant",
        "role": "primary",
        "conflict_class": "selected_wrong_positive_correct_present",
    },
    {
        "episode_key": "HM3D ObjectNav v2:val:7MXmsvcQjpJ:23:3:plant",
        "role": "primary",
        "conflict_class": "selected_wrong_positive_correct_present",
    },
]

SECONDARY_TARGETS = [
    {
        "episode_key": "HM3D ObjectNav v2:val:y9hTuugGdiq:11:1:sofa",
        "role": "secondary_stress",
        "conflict_class": "repeated_object_local_context_positive_conflict",
    },
    {
        "episode_key": "HM3D ObjectNav v2:val:y9hTuugGdiq:5:4:sofa",
        "role": "secondary_stress",
        "conflict_class": "repeated_object_local_context_positive_conflict",
    },
]

EXCLUDED_REGRESSION_ROWS = [
    "HM3D ObjectNav v2:val:y9hTuugGdiq:16:3:chair",
    "HM3D ObjectNav v2:val:y9hTuugGdiq:17:4:chair",
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def stable_hash(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def positive_support(candidate: Dict[str, Any]) -> bool:
    return (
        candidate.get("positive_support") is True
        or candidate.get("second_stage_strong_depth_evidence") is True
        or candidate.get("own_view_positive_support") is True
    )


def evidence_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("second_stage_candidate_evidence") or row.get("candidate_evidence") or [])


def summarize_evidence(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {
            "source_evidence_found": False,
            "positive_support_candidate_count": 0,
            "correct_positive_support_candidate_count": 0,
            "wrong_positive_support_candidate_count": 0,
            "selected_wrong_positive_support": False,
        }
    candidates = evidence_candidates(row)
    positives = [candidate for candidate in candidates if positive_support(candidate)]
    correct_positive = [candidate for candidate in positives if candidate.get("candidate_correct") is True]
    wrong_positive = [candidate for candidate in positives if candidate.get("candidate_correct") is False]
    selected_wrong_positive = any(
        candidate.get("identity_role") == "selected"
        and candidate.get("candidate_correct") is False
        and positive_support(candidate)
        for candidate in candidates
    )
    return {
        "source_evidence_found": True,
        "source_external_branch_id": row.get("external_branch_id"),
        "source_query": row.get("query"),
        "source_action": row.get("second_stage_identity_v1_action") or row.get("external_evidence_v1_action"),
        "source_reason": row.get("second_stage_identity_v1_reason") or row.get("external_evidence_v1_reason"),
        "positive_support_candidate_count": len(positives),
        "correct_positive_support_candidate_count": len(correct_positive),
        "wrong_positive_support_candidate_count": len(wrong_positive),
        "selected_wrong_positive_support": selected_wrong_positive,
        "positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in positives),
        "correct_positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in correct_positive),
        "wrong_positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in wrong_positive),
    }


def index_manifest_rows(paths: Iterable[Path]) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        manifest = load_json(path)
        for row in manifest.get("rows", []):
            key = str(row.get("episode_key"))
            if key in rows:
                raise ValueError(f"duplicate episode_key across source manifests: {key}")
            rows[key] = dict(row)
    return rows


def index_evidence_rows(paths: Iterable[Path]) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        for row in load_jsonl(path):
            key = str(row.get("episode_key"))
            if key:
                rows[key] = dict(row)
    return rows


def build_row(
    *,
    source_row: Dict[str, Any],
    target: Dict[str, Any],
    evidence_row: Optional[Dict[str, Any]],
    selected_split: str,
    seed: int,
    rank: int,
) -> Dict[str, Any]:
    row = dict(source_row)
    row["source_selected_split"] = source_row.get("selected_split")
    row["selected_split"] = selected_split
    row["selection_rank"] = rank
    row["selection_seed"] = seed
    row["deterministic_hash"] = stable_hash(seed, f"{selected_split}:{row['episode_key']}")
    row["dense_conflict_manifest_schema_version"] = SCHEMA_VERSION
    row["dense_conflict_role"] = target["role"]
    row["dense_conflict_class"] = target["conflict_class"]
    row.update({f"dense_conflict_{key}": value for key, value in summarize_evidence(evidence_row).items()})
    return row


def run(args: argparse.Namespace) -> Dict[str, Any]:
    source_manifests = [Path(args.primary_manifest), Path(args.secondary_manifest)]
    source_evidence = [Path(args.primary_evidence_rows), Path(args.secondary_evidence_rows)]
    manifest_rows = index_manifest_rows(source_manifests)
    evidence_rows = index_evidence_rows(source_evidence)

    targets = PRIMARY_TARGETS + SECONDARY_TARGETS
    output_rows: List[Dict[str, Any]] = []
    missing_manifest_keys: List[str] = []
    missing_evidence_keys: List[str] = []
    for rank, target in enumerate(targets):
        key = target["episode_key"]
        source_row = manifest_rows.get(key)
        evidence_row = evidence_rows.get(key)
        if source_row is None:
            missing_manifest_keys.append(key)
            continue
        if evidence_row is None:
            missing_evidence_keys.append(key)
        output_rows.append(
            build_row(
                source_row=source_row,
                target=target,
                evidence_row=evidence_row,
                selected_split=str(args.selected_split),
                seed=int(args.seed),
                rank=rank,
            )
        )

    role_counts = Counter(str(row.get("dense_conflict_role")) for row in output_rows)
    query_counts = Counter(str(row.get("target_or_query")) for row in output_rows)
    scene_counts = Counter(str(row.get("scene_key")) for row in output_rows)
    primary_rows = [row for row in output_rows if row.get("dense_conflict_role") == "primary"]
    primary_correct_wrong_positive = [
        row
        for row in primary_rows
        if int(row.get("dense_conflict_correct_positive_support_candidate_count") or 0) > 0
        and int(row.get("dense_conflict_wrong_positive_support_candidate_count") or 0) > 0
    ]
    primary_selected_wrong_positive = [
        row for row in primary_rows if row.get("dense_conflict_selected_wrong_positive_support") is True
    ]

    manifest = {
        "manifest_schema_version": SPLIT_SCHEMA_VERSION,
        "dense_conflict_manifest_schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creation_command": "python -m h001_runtime.build_dense_conflict_manifest",
        "selected_split": str(args.selected_split),
        "selection_seed": int(args.seed),
        "source_manifests": [str(path) for path in source_manifests],
        "source_evidence_rows": [str(path) for path in source_evidence],
        "excluded_regression_rows": EXCLUDED_REGRESSION_ROWS,
        "split_counts": {str(args.selected_split): len(output_rows)},
        "role_counts": dict(sorted(role_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "scene_counts": dict(sorted(scene_counts.items())),
        "primary_gate_precheck": {
            "primary_rows": len(primary_rows),
            "primary_rows_with_correct_and_wrong_positive_support": len(primary_correct_wrong_positive),
            "primary_rows_with_selected_wrong_positive_support": len(primary_selected_wrong_positive),
            "passes_target_precheck": (
                len(primary_rows) == 6
                and len(primary_correct_wrong_positive) == 6
                and len(primary_selected_wrong_positive) >= 3
            ),
        },
        "missing_manifest_keys": missing_manifest_keys,
        "missing_evidence_keys": missing_evidence_keys,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "rows": output_rows,
    }
    write_json(Path(args.out), manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the frozen H001 dense conflict validation manifest.")
    parser.add_argument("--primary-manifest", required=True)
    parser.add_argument("--secondary-manifest", required=True)
    parser.add_argument("--primary-evidence-rows", required=True)
    parser.add_argument("--secondary-evidence-rows", required=True)
    parser.add_argument("--selected-split", default=DEFAULT_SELECTED_SPLIT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
