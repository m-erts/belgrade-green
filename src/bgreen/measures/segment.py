"""Green View Index per image: share of pixels labelled Vegetation by Mask2Former (Swin-L)
trained on Mapillary Vistas, i.e. the same definition as the Global Streetscapes dataset.
Run with the project venv (torch); results are appended to a parquet so runs can resume."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

MODEL = "facebook/mask2former-swin-large-mapillary-vistas-semantic"
KEEP = ["Vegetation", "Terrain", "Sky", "Building", "Road", "Sidewalk", "Car"]


def run(paths: list[str], out: Path, device: str = "mps", flush_every: int = 200):
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, Mask2FormerForUniversalSegmentation

    done = set(pd.read_parquet(out)["path"]) if out.exists() else set()
    todo = [p for p in paths if p not in done]
    print(f"{len(done)} done, {len(todo)} to go", flush=True)
    if not todo:
        return
    proc = AutoImageProcessor.from_pretrained(MODEL)
    model = Mask2FormerForUniversalSegmentation.from_pretrained(MODEL).to(device).eval()
    id2label = model.config.id2label
    idx = {name: [k for k, v in id2label.items() if v == name] for name in KEEP}
    rows, t0 = [], time.time()
    for n, p in enumerate(todo, 1):
        try:
            img = Image.open(p).convert("RGB")
        except Exception:
            rows.append({"path": p, "ok": False})
            continue
        with torch.no_grad():
            inp = proc(images=img, return_tensors="pt").to(device)
            seg = proc.post_process_semantic_segmentation(model(**inp), target_sizes=[img.size[::-1]])[0]
        seg = seg.cpu().numpy()
        tot = seg.size
        row = {"path": p, "ok": True, "w": img.size[0], "h": img.size[1]}
        for name, ks in idx.items():
            row[name] = float(np.isin(seg, ks).sum() / tot)
        rows.append(row)
        if n % flush_every == 0 or n == len(todo):
            new = pd.DataFrame(rows)
            old = pd.read_parquet(out) if out.exists() else None
            (pd.concat([old, new]) if old is not None else new).to_parquet(out)
            rows = []
            print(f"{n}/{len(todo)}  {(time.time() - t0) / n:.2f} s/img", flush=True)


if __name__ == "__main__":
    lst, out = sys.argv[1], Path(sys.argv[2])
    run(Path(lst).read_text().split(), out)
