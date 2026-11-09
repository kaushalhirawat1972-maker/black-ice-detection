"""
Black ice detector using trained YOLO model.
"""

import os
import tempfile
# Ensure writable cache paths
if "YOLO_CONFIG_DIR" not in os.environ:
    os.environ["YOLO_CONFIG_DIR"] = tempfile.gettempdir()
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

import time
from pathlib import Path
from typing import List, Tuple, Optional, Union, Dict, Any
import numpy as np
import cv2
from PIL import Image
from ultralytics import YOLO
import torch


class BlackIceDetector:
    """Black ice detector using YOLOv8."""

    def __init__(
        self,
        model_path: str | Path = "models/checkpoints/black_ice/weights/best.pt",
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: str = "cuda:1"
    ):
        """
        Initialize black ice detector.

        Args:
            model_path: Path to trained YOLO model
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            device: Device to run inference on (cuda:1, cuda:0, cuda, cpu, mps)
        """
        self.model_path = Path(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

        # Check device availability
        if device.startswith("cuda") and not torch.cuda.is_available():
            print("⚠ CUDA not available, using CPU")
            device = "cpu"
        elif device == "mps" and not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
            print("⚠ MPS not available, using CPU")
            device = "cpu"

        self.device = device

        # Load model
        print(f"Loading model from: {self.model_path}")
        self.model = YOLO(str(self.model_path))
        self.model.to(device)

        print(f"✓ Model loaded on {device}")

        # Warmup
        self._warmup()

    def _warmup(self, img_size: int = 640):
        """Warmup model with dummy inference."""
        try:
            dummy_img = np.zeros((img_size, img_size, 3), dtype=np.uint8)
            self.detect(dummy_img)
        except Exception as e:
            print(f"Warmup notice: {e}")

    def load_image(self, image: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """
        Load and standardize image to BGR numpy array.

        Args:
            image: Image file path, numpy array, or PIL Image

        Returns:
            np.ndarray in BGR format
        """
        if isinstance(image, (str, Path)):
            path = Path(image)
            if not path.exists():
                raise FileNotFoundError(f"Image not found at {path}")
            img = cv2.imread(str(path))
            if img is None:
                raise ValueError(f"Failed to read image at {path}")
            return img
        elif isinstance(image, np.ndarray):
            return image
        elif isinstance(image, Image.Image):
            rgb = np.array(image.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")

    def detect(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        visualize: bool = False
    ) -> List[dict]:
        """
        Detect black ice patches in image.

        Args:
            image: Input image (BGR format, file path, or PIL Image)
            visualize: Whether to plot detections

        Returns:
            List of detections, each containing:
                - bbox: [x_center, y_center, w, h] (normalized 0-1)
                - bbox_xyxy: [x1, y1, x2, y2] in pixel coordinates
                - confidence: Detection confidence
                - class_id: Class ID (0 for black_ice)
                - class_name: Class name
        """
        img = self.load_image(image)

        results = self.model.predict(
            img,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False
        )[0]

        detections = []

        if results.boxes is not None and len(results.boxes) > 0:
            boxes = results.boxes
            img_h, img_w = img.shape[:2]

            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = xyxy

                x_center = ((x1 + x2) / 2) / img_w
                y_center = ((y1 + y2) / 2) / img_h
                width = (x2 - x1) / img_w
                height = (y2 - y1) / img_h

                confidence = float(boxes.conf[i])
                class_id = int(boxes.cls[i])
                class_name = self.model.names.get(class_id, "black_ice")

                detections.append({
                    'bbox': [float(x_center), float(y_center), float(width), float(height)],
                    'bbox_xyxy': [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))],
                    'confidence': confidence,
                    'class_id': class_id,
                    'class_name': class_name
                })

        if visualize and results.plot is not None:
            results.plot()

        return detections

    def predict_image(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Core vision inference: Input an image and output if it is black ice or not.

        Args:
            image: Image file path, numpy BGR array, or PIL Image
            conf_threshold: Optional confidence threshold override

        Returns:
            Dictionary containing:
                - is_black_ice: bool (True if black ice detected, False otherwise)
                - label: str ("BLACK_ICE" vs "NO_ICE")
                - ice_confidence: float (highest detection confidence, 0.0 if none)
                - patch_bbox: Optional[Tuple[int, int, int, int]] (primary [x1, y1, x2, y2] in pixels)
                - patch_bbox_norm: Optional[List[float]] (normalized [x_center, y_center, w, h])
                - detections: List[dict] (all detected patches)
                - num_patches: int
                - image_shape: Tuple[int, int] (height, width)
        """
        img = self.load_image(image)
        h, w = img.shape[:2]

        saved_conf = self.conf_threshold
        if conf_threshold is not None:
            self.conf_threshold = conf_threshold

        try:
            detections = self.detect(img)
        finally:
            self.conf_threshold = saved_conf

        is_black_ice = len(detections) > 0
        if is_black_ice:
            # Pick the highest confidence detection as primary patch
            best_det = max(detections, key=lambda d: d['confidence'])
            ice_confidence = float(best_det['confidence'])
            patch_bbox = tuple(best_det['bbox_xyxy'])
            patch_bbox_norm = list(best_det['bbox'])
        else:
            ice_confidence = 0.0
            patch_bbox = None
            patch_bbox_norm = None

        return {
            "is_black_ice": is_black_ice,
            "label": "BLACK_ICE" if is_black_ice else "NO_ICE",
            "ice_confidence": ice_confidence,
            "patch_bbox": patch_bbox,
            "patch_bbox_norm": patch_bbox_norm,
            "detections": detections,
            "num_patches": len(detections),
            "image_shape": (h, w)
        }

    def __call__(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        conf_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calling detector(image) directly returns black ice classification."""
        return self.predict_image(image, conf_threshold=conf_threshold)

    def detect_with_timing(
        self,
        image: Union[str, Path, np.ndarray, Image.Image]
    ) -> Tuple[List[dict], float]:
        """Detect with timing information in milliseconds."""
        start_time = time.time()
        detections = self.detect(image)
        inference_time = (time.time() - start_time) * 1000.0
        return detections, inference_time

    def get_coverage_percentage(self, detections: List[dict]) -> float:
        """Calculate estimated black ice coverage percentage."""
        if not detections:
            return 0.0
        total_area = sum(det['bbox'][2] * det['bbox'][3] for det in detections)
        return min(total_area * 100.0, 100.0)

    def get_highest_confidence(self, detections: List[dict]) -> Optional[float]:
        """Get highest confidence among detections."""
        if not detections:
            return None
        return max(det['confidence'] for det in detections)

    def update_thresholds(
        self,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ):
        """Update detection thresholds."""
        if conf_threshold is not None:
            self.conf_threshold = conf_threshold
        if iou_threshold is not None:
            self.iou_threshold = iou_threshold


class ONNXDetector:
    """Black ice detector using ONNX Runtime (for deployment)."""

    def __init__(
        self,
        onnx_path: str | Path,
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        img_size: int = 640
    ):
        import onnxruntime as ort

        self.onnx_path = Path(onnx_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.img_size = img_size

        print(f"Loading ONNX model from: {self.onnx_path}")
        self.session = ort.InferenceSession(str(self.onnx_path))
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [out.name for out in self.session.get_outputs()]
        print(f"✓ ONNX model loaded: {self.input_name} -> {self.output_names}")

    def preprocess(self, image: np.ndarray) -> np.ndarray:
        img = cv2.resize(image, (self.img_size, self.img_size))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)
        img = np.expand_dims(img, axis=0)
        return img

    def detect(self, image: np.ndarray) -> List[dict]:
        input_tensor = self.preprocess(image)
        outputs = self.session.run(self.output_names, {self.input_name: input_tensor})
        return self._postprocess(outputs, image.shape[:2])

    def _postprocess(self, outputs: List[np.ndarray], img_shape: Tuple[int, int]) -> List[dict]:
        return []


def test_detector(model_path: str | Path, image_path: str | Path):
    """Test detector on a single image and output whether it is black ice or not."""
    detector = BlackIceDetector(model_path)
    result = detector.predict_image(image_path)

    print("\n" + "=" * 50)
    print("BLACK ICE VISION PREDICTION RESULT")
    print("=" * 50)
    print(f"Input image:        {image_path}")
    print(f"Is Black Ice?       {result['is_black_ice']}")
    print(f"Classification:     {result['label']}")
    print(f"Ice Confidence:     {result['ice_confidence']:.3f}")
    print(f"Primary Patch BBox: {result['patch_bbox']}")
    print(f"Total Patches:      {result['num_patches']}")
    print("=" * 50)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python detector.py <model_path> <image_path>")
        sys.exit(1)
    test_detector(sys.argv[1], sys.argv[2])
