"""
Test YOLOv8 Black Ice Detection Model on images.

Quick usage:
  python test_model_predictions.py
  python test_model_predictions.py --source "path/to/any_image.jpg"
  python test_model_predictions.py --max 20 --conf 0.3
"""

import argparse
import os
import sys
from pathlib import Path
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Test Black Ice YOLOv8 Model on Images")
    parser.add_argument(
        "--source",
        type=str,
        default="data/processed/images/test/OD",
        help="Path to an image file or folder containing images (default: data/processed/images/test/OD)"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="models/checkpoints/black_ice/weights/best.pt",
        help="Path to trained model weights"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold for detections (default: 0.25)"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="Max images to evaluate from folder (default: 10, set 0 for all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="predictions",
        help="Folder to save visualized output images (default: predictions)"
    )
    args = parser.parse_args()

    # 1. Verify model weights
    weights_path = Path(args.weights)
    if not weights_path.exists():
        print(f"❌ Error: Model weights not found at: {weights_path}")
        sys.exit(1)

    print("=" * 70)
    print("🧊 BLACK ICE DETECTION — MODEL INFERENCE TEST")
    print(f"📁 Weights: {weights_path}")
    print(f"🎯 Confidence Threshold: {args.conf}")
    print("=" * 70)

    model = YOLO(str(weights_path))

    # 2. Collect images
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Error: Source path does not exist: {source_path}")
        sys.exit(1)

    valid_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    if source_path.is_file():
        image_paths = [source_path]
    else:
        # Search directory and subdirectories
        image_paths = [p for p in source_path.rglob("*") if p.suffix.lower() in valid_exts]
        if args.max > 0 and len(image_paths) > args.max:
            print(f"ℹ Found {len(image_paths)} images in source. Running on first {args.max} images...")
            image_paths = image_paths[:args.max]

    if not image_paths:
        print(f"❌ No valid images found in {source_path}")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 Running inference on {len(image_paths)} image(s)...")
    print("-" * 70)

    detected_count = 0
    total_patches = 0

    for i, img_path in enumerate(image_paths, 1):
        # Run prediction and save annotated image
        results = model.predict(
            source=str(img_path),
            conf=args.conf,
            save=True,
            project=str(output_dir),
            name="visualized",
            exist_ok=True,
            verbose=False
        )

        res = results[0]
        boxes = res.boxes
        num_boxes = len(boxes)

        short_name = img_path.name
        if len(short_name) > 35:
            short_name = short_name[:15] + "..." + short_name[-15:]

        if num_boxes > 0:
            detected_count += 1
            total_patches += num_boxes
            confs_str = ", ".join([f"{float(c)*100:.1f}%" for c in boxes.conf])
            print(f"[{i:02d}/{len(image_paths):02d}] 🚨 {short_name:<35} -> {num_boxes} Black Ice patch(es) detected! | Conf: [{confs_str}]")
        else:
            print(f"[{i:02d}/{len(image_paths):02d}] ⚪ {short_name:<35} -> Clear (No ice above {args.conf*100:.0f}% confidence)")

    save_location = output_dir / "visualized"
    print("-" * 70)
    print("📊 TEST SUMMARY:")
    print(f"  • Total Images Tested: {len(image_paths)}")
    print(f"  • Images with Black Ice Detected: {detected_count} ({detected_count/len(image_paths)*100:.1f}%)")
    print(f"  • Total Black Ice Patches Detected: {total_patches}")
    print(f"  • Visualized images with bounding boxes saved in:")
    print(f"    👉 {save_location.resolve()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
