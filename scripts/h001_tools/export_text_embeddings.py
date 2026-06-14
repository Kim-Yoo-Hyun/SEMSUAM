import argparse
import json
import os
import re
from pathlib import Path
from typing import List

import clip
import numpy as np
import torch


CLIP_DIMS = {
    "RN50": 1024,
    "RN101": 512,
    "RN50x4": 640,
    "RN50x16": 768,
    "RN50x64": 1024,
    "ViT-B/32": 512,
    "ViT-B/16": 512,
    "ViT-L/14": 768,
}


def slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return value or "query"


def read_queries(args: argparse.Namespace) -> List[str]:
    queries: List[str] = []
    if args.queries:
        queries.extend(args.queries)
    if args.query_file:
        for line in Path(args.query_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)
    seen = set()
    unique = []
    for query in queries:
        if query not in seen:
            seen.add(query)
            unique.append(query)
    if not unique:
        raise ValueError("no queries provided")
    return unique


def choose_device(device: str) -> str:
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    return device


def export_embeddings(args: argparse.Namespace) -> dict:
    queries = read_queries(args)
    device = choose_device(args.device)
    expected_dim = CLIP_DIMS[args.model]

    model, _ = clip.load(args.model, device=device, jit=False)
    model.eval()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    with torch.no_grad():
        for start in range(0, len(queries), args.batch_size):
            batch = queries[start : start + args.batch_size]
            tokens = clip.tokenize(batch).to(device)
            feats = model.encode_text(tokens).float()
            feats = feats / feats.norm(dim=-1, keepdim=True)
            feats_np = feats.cpu().numpy().astype(np.float32)

            for query, emb in zip(batch, feats_np):
                if emb.shape != (expected_dim,):
                    raise ValueError(f"unexpected embedding shape for {query}: {emb.shape}")
                name = f"{slug(query)}.npy"
                path = out_dir / name
                np.save(path, emb)
                rows.append(
                    {
                        "query": query,
                        "embedding_path": str(path),
                        "dim": int(emb.shape[0]),
                        "l2_norm": float(np.linalg.norm(emb)),
                    }
                )

    manifest = {
        "backend": "openai_clip_text",
        "model": args.model,
        "device": device,
        "clip_commit": os.environ.get("OPENAI_CLIP_COMMIT"),
        "uses_gt_for_action": False,
        "queries": rows,
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export VLMaps-compatible CLIP text embeddings.")
    parser.add_argument("--queries", nargs="*", default=None)
    parser.add_argument("--query-file", default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--model", default="ViT-B/32", choices=sorted(CLIP_DIMS))
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--batch-size", type=int, default=64)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = export_embeddings(args)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
