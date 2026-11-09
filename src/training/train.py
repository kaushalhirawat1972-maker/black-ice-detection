"""
Training script for YOLOv8 black ice detection model.
"""

import sys
import argparse
from pathlib import Path
import torch
from ultralytics import YOLO
import yaml


def train_model(
    data_yaml: str | Path,
    model_name: str = "yolov8s.pt",
    epochs: int = 100,
    batch_size: int = 16,
    img_size: int = 640,
    device: str = "cuda:0",
    project: str = "models/checkpoints",
    name: str = "black_ice",
    **kwargs
):
    """
    Train YOLOv8 model for black ice detection.

    Args:
        data_yaml: Path to data.yaml configuration
        model_name: Model variant (yolov8n/s/m/l/x.pt)
        epochs: Number of training epochs
        batch_size: Batch size
        img_size: Input image size
        device: Device to train on (cuda/cpu/mps)
        project: Project directory for saving runs
        name: Run name
        **kwargs: Additional training arguments
    """
    print("=" * 60)
    print("YOLOv8 Black Ice Detection Training")
    print("=" * 60)

    # Check device availability
    if device.startswith("cuda") and not torch.cuda.is_available():
        print("⚠ CUDA not available, switching to CPU")
        device = "cpu"
    elif device == "mps" and not torch.backends.mps.is_available():
        print("⚠ MPS not available, switching to CPU")
        device = "cpu"

    if device.startswith("cuda") and torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        gpu_idx = int(device.split(":")[1]) if ":" in device else 0
        if gpu_idx >= gpu_count:
            print(f"⚠ Requested {device}, but found {gpu_count} GPU(s). Auto-selecting cuda:0 ({torch.cuda.get_device_name(0)})")
            gpu_idx = 0
            device = "cuda:0"
        print(f"Device: {device} (GPU [{gpu_idx}]: {torch.cuda.get_device_name(gpu_idx)})")
        print(f"GPU Memory: {torch.cuda.get_device_properties(gpu_idx).total_memory / 1024**3:.2f} GB")
    else:
        print(f"Device: {device}")

    # Load model
    print(f"\nLoading model: {model_name}")
    model = YOLO(model_name)

    # Display model info
    print(f"Model parameters: {sum(p.numel() for p in model.model.parameters()):,}")

    # Verify data.yaml
    data_yaml_path = Path(data_yaml)
    if not data_yaml_path.exists():
        raise FileNotFoundError(f"data.yaml not found: {data_yaml_path}")

    with open(data_yaml_path, 'r') as f:
        data_config = yaml.safe_load(f)

    print(f"\nDataset: {data_yaml_path}")
    print(f"Classes: {data_config.get('names', [])}")
    print(f"Number of classes: {data_config.get('nc', 0)}")

    # Training parameters
    print(f"\nTraining parameters:")
    print(f"  Epochs: {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  Image size: {img_size}")
    print(f"  Device: {device}")

    # Start training
    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60 + "\n")

    results = model.train(
        data=str(data_yaml_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=device,
        project=project,
        name=name,
        exist_ok=True,
        pretrained=True,
        verbose=True,
        **kwargs
    )

    # Training summary
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)

    # Save best model path
    best_model_path = Path(project) / name / "weights" / "best.pt"
    print(f"\nBest model saved to: {best_model_path}")

    # Display metrics
    if hasattr(results, 'results_dict'):
        metrics = results.results_dict
        print("\nFinal Metrics:")
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                print(f"  {key}: {value:.4f}")

    print("\nNext steps:")
    print(f"  1. Evaluate: python src/training/evaluate.py --model {best_model_path}")
    print(f"  2. Export: python src/training/export.py --model {best_model_path}")

    return results


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(
        description="Train YOLOv8 for black ice detection"
    )

    # Data
    parser.add_argument(
        "--data",
        type=str,
        default="data/processed/data.yaml",
        help="Path to data.yaml"
    )

    # Model
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8s.pt",
        help="Model variant (yolov8n/s/m/l/x.pt)"
    )

    # Training hyperparameters
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Number of epochs"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=16,
        help="Batch size"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Image size"
    )

    # Device
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="Device (cuda:0, cuda:1, cpu, mps) — default cuda:1 = RTX 3050"
    )

    # Output
    parser.add_argument(
        "--project",
        type=str,
        default="models/checkpoints",
        help="Project directory"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="black_ice",
        help="Run name"
    )

    # Additional YOLO arguments
    parser.add_argument(
        "--patience",
        type=int,
        default=20,
        help="Early stopping patience"
    )
    parser.add_argument(
        "--save-period",
        type=int,
        default=-1,
        help="Save checkpoint every N epochs (-1 to disable)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of data loading workers"
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Cache images for faster training"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from last checkpoint"
    )

    # Load config
    parser.add_argument(
        "--config",
        type=str,
        help="Load parameters from YAML config file"
    )

    args = parser.parse_args()

    # Load config if provided
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Override args with config values
            training_config = config.get('training', {})
            for key, value in training_config.items():
                if hasattr(args, key):
                    setattr(args, key, value)

            inference_config = config.get('inference', {})
            if 'device' in inference_config:
                args.device = inference_config['device']

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    data_yaml = project_root / args.data
    project_dir = project_root / args.project

    # Additional training kwargs
    training_kwargs = {
        'patience': args.patience,
        'save_period': args.save_period,
        'workers': args.workers,
        'cache': args.cache,
        'resume': args.resume,
    }

    # Train
    try:
        train_model(
            data_yaml=data_yaml,
            model_name=args.model,
            epochs=args.epochs,
            batch_size=args.batch,
            img_size=args.imgsz,
            device=args.device,
            project=str(project_dir),
            name=args.name,
            **training_kwargs
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
