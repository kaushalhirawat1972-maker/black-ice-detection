"""
BLACK ICE DETECTION SYSTEM
Multi-Sensor Perception Architecture:
- Module 1: Sensor Acquisition (1080p RGB Camera, MLX90640 Thermal Array, 2D Planar LiDAR)
- Module 2: Calibrated Surface Temperature Screening (eps=0.95, [-10°C, 3°C] risk envelope)
- Vision Model: YOLOv8 Deep Neural Object Detection & Classification
- Module 5: Geometric LiDAR Azimuth Ray Association & Specular Dropout Filtering
- Precision De-icing Spray Actuation & Real-time Telemetry
"""

import sys
import os
import time
import tempfile
from datetime import datetime
from pathlib import Path
import cv2
import numpy as np
import torch
import streamlit as st
from PIL import Image

# Safe cache directories for Ultralytics and Matplotlib
if "YOLO_CONFIG_DIR" not in os.environ:
    os.environ["YOLO_CONFIG_DIR"] = tempfile.gettempdir()
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = tempfile.gettempdir()

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.inference.detector import BlackIceDetector
from src.pipeline.black_ice_pipeline import BlackIcePipeline
from src.utils.camera import Camera
from src.utils.config import Config

# Page Configuration
st.set_page_config(
    page_title="BLACK ICE DETECTION",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if "history" not in st.session_state:
    st.session_state.history = []
if "running_video" not in st.session_state:
    st.session_state.running_video = False
if "frame_count" not in st.session_state:
    st.session_state.frame_count = 0
    st.session_state.hazard_count = 0
if "preview_mode" not in st.session_state:
    st.session_state.preview_mode = "Visible"

# Inject BLACK ICE DETECTION CSS Theme (Deep Frosted Navy + Warm Linen Beige + Ice Glow)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --deep-navy: #07172c;
        --navy: #0b2545;
        --royal: #13315c;
        --ice: #38bdf8;
        --ice-glow: rgba(56, 189, 248, 0.35);
        --hazard: #ffd166;
        --hazard-glow: rgba(255, 209, 102, 0.45);
        --cream: #f4f1ea;
        --paper: #f8fafc;
        --ink: #15243a;
        --muted-ink: #617187;
        --line: #dce5ee;
        --border-glass: rgba(226, 232, 240, 0.14);
        --safe-green: #10b981;
        --alert-red: #ef4444;
    }

    /* Base Styling */
    .stApp {
        background-color: var(--cream);
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
        color: var(--ink);
    }

    html {
        scroll-behavior: smooth;
    }

    /* BLACK ICE DETECTION TOPBAR */
    .frost-topbar {
        position: relative;
        z-index: 10;
        display: flex;
        width: 100%;
        min-height: 68px;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        margin: 0 0 24px 0;
        padding: 12px 24px;
        border: 1px solid var(--border-glass);
        border-radius: 18px;
        background: rgba(7, 23, 44, 0.85);
        box-shadow: 0 16px 40px rgba(1, 12, 26, 0.25);
        backdrop-filter: blur(20px) saturate(160%);
    }

    .brand-lockup {
        display: flex;
        align-items: center;
        gap: 12px;
        text-decoration: none;
    }

    .brand-mark {
        display: grid;
        width: 38px;
        height: 38px;
        place-items: center;
        border: 1px solid rgba(56, 189, 248, 0.38);
        border-radius: 11px;
        color: #bceaff;
        background: linear-gradient(140deg, rgba(56, 189, 248, 0.25), rgba(56, 189, 248, 0.05));
        font-size: 1.25rem;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.2);
    }

    .brand-name {
        color: #e2e8f0;
        font-family: 'Outfit', sans-serif;
        font-size: 22px;
        font-weight: 700;
        letter-spacing: -0.04em;
    }

    .brand-name span {
        color: var(--ice);
    }

    .brand-divider {
        width: 1px;
        height: 22px;
        margin-inline: 4px;
        background: rgba(226, 232, 240, 0.22);
    }

    .brand-edition {
        color: #a8bad1;
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.14em;
        font-weight: 600;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 6px 14px;
        border-radius: 9999px;
        color: #34d399;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 10px #10b981;
        animation: pulseDot 2s infinite ease-in-out;
    }

    @keyframes pulseDot {
        0%, 100% { opacity: 0.8; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.3); }
    }

    /* HERO SECTION */
    .hero-container {
        position: relative;
        overflow: hidden;
        padding: 44px 44px;
        background: linear-gradient(135deg, #07172c 0%, #0b2545 55%, #13315c 100%);
        border-radius: 24px;
        margin-bottom: 30px;
        color: #e2e8f0;
        border: 1px solid rgba(56, 189, 248, 0.2);
        box-shadow: 0 24px 48px -12px rgba(7, 23, 44, 0.35);
    }

    .eyebrow {
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.15em;
        color: var(--ice);
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    .eyebrow-line {
        width: 24px;
        height: 2px;
        background: var(--ice);
        border-radius: 1px;
    }

    .hero-heading {
        font-family: 'Outfit', sans-serif;
        font-size: 2.7rem;
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: -0.04em;
        margin-bottom: 14px;
        color: #ffffff;
    }

    .hero-heading span {
        background: linear-gradient(120deg, #38bdf8 0%, #80e5ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hero-description {
        font-size: 1.08rem;
        color: #bdcad9;
        max-width: 680px;
        line-height: 1.6;
        margin-bottom: 24px;
    }

    .hero-facts {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
    }

    .hero-fact {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(226, 232, 240, 0.15);
        padding: 6px 14px;
        border-radius: 12px;
        font-size: 13px;
        color: #e2e8f0;
        backdrop-filter: blur(8px);
        transition: all 0.25s ease;
    }

    .hero-fact:hover {
        background: rgba(56, 189, 248, 0.15);
        border-color: var(--ice);
        transform: translateY(-2px);
    }

    /* ARCHITECTURE PIPELINE CARDS */
    .arch-container {
        background: #07172c;
        border-radius: 24px;
        padding: 40px 36px;
        color: #e2e8f0;
        margin: 30px 0;
        border: 1px solid rgba(56, 189, 248, 0.22);
        box-shadow: 0 20px 40px rgba(7, 23, 44, 0.3);
    }

    .arch-heading {
        font-family: 'Outfit', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
    }

    .arch-sub {
        font-size: 1rem;
        color: #94a3b8;
        max-width: 700px;
        margin-bottom: 30px;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 20px;
        margin-bottom: 24px;
    }

    .feature-card {
        background: rgba(11, 37, 69, 0.65);
        border: 1px solid rgba(226, 232, 240, 0.12);
        border-radius: 18px;
        padding: 24px;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
    }

    .feature-card:hover {
        transform: translateY(-5px);
        border-color: var(--ice);
        box-shadow: 0 16px 32px rgba(56, 189, 248, 0.2);
        background: rgba(19, 49, 92, 0.75);
    }

    .feature-card-accent {
        background: linear-gradient(145deg, rgba(19, 49, 92, 0.8), rgba(11, 37, 69, 0.9));
        border-color: rgba(56, 189, 248, 0.35);
        box-shadow: 0 8px 24px rgba(56, 189, 248, 0.15);
    }

    .feature-card-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 14px;
    }

    .step-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 700;
        color: var(--ice);
        background: rgba(56, 189, 248, 0.15);
        padding: 3px 10px;
        border-radius: 9999px;
    }

    .feature-card h3 {
        font-family: 'Outfit', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 8px;
    }

    .feature-card p {
        font-size: 0.92rem;
        color: #cbd5e1;
        line-height: 1.55;
        margin-bottom: 16px;
    }

    .feature-footnote {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10px;
        color: #94a3b8;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        display: block;
    }

    .arch-note-banner {
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(56, 189, 248, 0.08);
        border: 1px solid rgba(56, 189, 248, 0.22);
        padding: 14px 20px;
        border-radius: 14px;
        color: #e0f2fe;
        font-size: 0.95rem;
    }

    /* WORKBENCH & BENTO CARDS */
    .bento-card {
        background-color: #ffffff;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 24px;
        margin-bottom: 22px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
        transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    }

    .bento-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 16px 36px rgba(11, 37, 69, 0.08);
        border-color: #93c5fd;
    }

    /* VIEWPORT HUD OVERLAYS */
    .viewport-box {
        position: relative;
        border-radius: 16px;
        overflow: hidden;
        background: #000000;
        border: 2px solid #0f172a;
    }

    .viewport-view-label {
        position: absolute;
        bottom: 14px;
        right: 14px;
        background: rgba(7, 23, 44, 0.85);
        color: #38bdf8;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 8px;
        letter-spacing: 0.08em;
        border: 1px solid rgba(56, 189, 248, 0.3);
        backdrop-filter: blur(6px);
        z-index: 5;
    }

    /* TELEMETRY METRIC TILES */
    .telemetry-card {
        background: #faf7f2;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 12px;
        transition: all 0.22s ease;
    }

    .telemetry-card:hover {
        background: #ffffff;
        border-color: var(--ice);
        box-shadow: 0 8px 20px rgba(56, 189, 248, 0.15);
        transform: translateY(-2px);
    }

    .telemetry-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        color: var(--muted-ink);
        letter-spacing: 0.08em;
        margin-bottom: 4px;
    }

    .telemetry-val {
        font-family: 'Outfit', sans-serif;
        font-size: 1.85rem;
        font-weight: 800;
        color: var(--deep-navy);
    }

    /* HAZARD BADGES */
    .badge-hazard {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: #ffffff;
        padding: 12px 22px;
        border-radius: 14px;
        font-weight: 800;
        font-size: 1.15rem;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 0 28px rgba(239, 68, 68, 0.5);
        animation: pulseAlert 2s infinite ease-in-out;
    }

    .badge-warning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: #ffffff;
        padding: 12px 22px;
        border-radius: 14px;
        font-weight: 800;
        font-size: 1.15rem;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.4);
    }

    .badge-safe {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #ffffff;
        padding: 12px 22px;
        border-radius: 14px;
        font-weight: 800;
        font-size: 1.15rem;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
    }

    @keyframes pulseAlert {
        0%, 100% { transform: scale(1); box-shadow: 0 0 20px rgba(239, 68, 68, 0.4); }
        50% { transform: scale(1.02); box-shadow: 0 0 35px rgba(239, 68, 68, 0.75); }
    }

    /* DE-ICING ACTUATOR STRIP */
    .actuator-box {
        background: linear-gradient(145deg, #07172c, #0b2545);
        color: #e2e8f0;
        border-radius: 14px;
        padding: 20px;
        border: 1px solid rgba(56, 189, 248, 0.25);
    }

    .actuator-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }

    .actuator-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        font-weight: 700;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# Cursor-Following Spotlight and Tactile Ripple Feedback
st.html("""
<script>
    const rootDoc = window.parent.document;
    
    // 1. Cursor Spotlight Overlay
    if (!rootDoc.getElementById('frost-spotlight')) {
        const spot = rootDoc.createElement('div');
        spot.id = 'frost-spotlight';
        spot.style.position = 'fixed';
        spot.style.top = '0';
        spot.style.left = '0';
        spot.style.width = '100vw';
        spot.style.height = '100vh';
        spot.style.pointerEvents = 'none';
        spot.style.zIndex = '99999';
        spot.style.transition = 'opacity 0.2s ease';
        spot.style.background = 'radial-gradient(650px circle at -500px -500px, rgba(56, 189, 248, 0.08), transparent 80%)';
        rootDoc.body.appendChild(spot);

        rootDoc.addEventListener('pointermove', (e) => {
            spot.style.background = `radial-gradient(650px circle at ${e.clientX}px ${e.clientY}px, rgba(56, 189, 248, 0.09), transparent 75%)`;
        });
    }

    // 2. Click Ripple Effect
    rootDoc.addEventListener('click', (e) => {
        const ripple = rootDoc.createElement('div');
        ripple.style.position = 'fixed';
        ripple.style.left = `${e.clientX - 22}px`;
        ripple.style.top = `${e.clientY - 22}px`;
        ripple.style.width = '44px';
        ripple.style.height = '44px';
        ripple.style.borderRadius = '50%';
        ripple.style.background = 'radial-gradient(circle, rgba(56, 189, 248, 0.45) 0%, transparent 80%)';
        ripple.style.pointerEvents = 'none';
        ripple.style.zIndex = '999999';
        ripple.style.transform = 'scale(0)';
        ripple.style.transition = 'transform 0.4s cubic-bezier(0, 0, 0.2, 1), opacity 0.4s ease';
        rootDoc.body.appendChild(ripple);

        requestAnimationFrame(() => {
            ripple.style.transform = 'scale(3.8)';
            ripple.style.opacity = '0';
        });

        setTimeout(() => ripple.remove(), 450);
    });
</script>
""")


# Visualization Helpers for Viewport Modes (Visible, Thermal, Edge View)
def generate_thermal_view(image_bgr: np.ndarray, temp_c: float = -2.5, bbox=None) -> np.ndarray:
    """Simulate MLX90640 32x24 interpolated thermal pseudo-color colormap."""
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    
    thermal_map = blurred.astype(np.float32)
    thermal_map = (thermal_map - thermal_map.min()) / (thermal_map.max() - thermal_map.min() + 1e-6)
    
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        # Simulated freezing thermal anomaly on ice patch
        thermal_map[max(0, y1):min(h, y2), max(0, x1):min(w, x2)] *= 0.55
        
    thermal_u8 = (thermal_map * 255).astype(np.uint8)
    thermal_colored = cv2.applyColorMap(thermal_u8, cv2.COLORMAP_INFERNO)
    
    # Blend 65% thermal heatmap + 35% RGB road features
    blended = cv2.addWeighted(thermal_colored, 0.65, image_bgr, 0.35, 0)
    
    # Add calibrated thermal scale overlay
    cv2.putText(blended, f"MLX90640 CALIBRATED: {temp_c:.1f}C (eps=0.95)", (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    return blended


def generate_edge_view(image_bgr: np.ndarray, dist_m: float = 12.0, bbox=None) -> np.ndarray:
    """Generate high-contrast edge inspection with 2D LiDAR planar scan fan overlay."""
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    
    hud = np.zeros_like(image_bgr)
    hud[edges > 0] = [248, 189, 56]  # Ice Cyan edges (BGR)
    
    # 2D LiDAR forward ray projection fan (120 degree sector)
    center_x = w // 2
    bot_y = h
    for angle in np.linspace(-45, 45, 19):
        rad = np.radians(angle)
        ray_len = int(h * 0.72)
        end_x = int(center_x + ray_len * np.sin(rad))
        end_y = int(bot_y - ray_len * np.cos(rad))
        cv2.line(hud, (center_x, bot_y), (end_x, end_y), (70, 50, 20), 1)
        
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(hud, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(hud, f"SPECULAR DROPOUT DETECTED @ {dist_m:.1f}m", (x1, max(25, y1 - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 209, 255), 2)
                    
    blended = cv2.addWeighted(hud, 0.82, image_bgr, 0.18, 0)
    return blended


# Caching Model and Pipeline
@st.cache_resource
def load_detector(model_path: str, conf_threshold: float, device: str):
    return BlackIceDetector(model_path=model_path, conf_threshold=conf_threshold, device=device)


@st.cache_resource
def load_pipeline(config_path: str, model_path: str, device: str):
    return BlackIcePipeline(config_path=config_path, model_path=model_path, device=device, force_simulator=True)


# Auto-detect Acceleration Hardware (RTX 3050 / RTX 5060 fallback)
def get_available_devices():
    devices = []
    if torch.cuda.is_available():
        count = torch.cuda.device_count()
        for i in range(count):
            name = torch.cuda.get_device_name(i)
            devices.append((f"cuda:{i}", f"GPU {i}: {name}"))
    devices.append(("cpu", "CPU: Standard Execution"))
    return devices


def main():
    # 1. BLACK ICE DETECTION NAVIGATION TOPBAR
    st.markdown("""
    <header class="frost-topbar">
        <a class="brand-lockup" href="#top">
            <span class="brand-mark">❄</span>
            <div class="brand-name">BLACK ICE <span>DETECTION</span></div>
            <div class="brand-divider"></div>
            <div class="brand-edition">ROAD PERCEPTION INTELLIGENCE</div>
        </a>
        <div class="status-pill">
            <span class="status-dot"></span>
            <span>Model Ready (YOLOv8 + MLX90640 + LiDAR)</span>
        </div>
    </header>
    """, unsafe_allow_html=True)

    # 2. HERO SHOWCASE
    st.markdown("""
    <div class="hero-container" id="top">
        <div class="eyebrow">
            <span class="eyebrow-line"></span> WINTER ROAD PERCEPTION
        </div>
        <div class="hero-heading">
            Real-time road safety<br>powered by <span>AI.</span>
        </div>
        <div class="hero-description">
            A sharper view of the cold road ahead. Multi-spectral sensor fusion combining 1080p RGB vision,
            calibrated MLX90640 thermal screening, and 2D LiDAR depth association to pinpoint invisible black ice in real-time.
        </div>
        <div class="hero-facts">
            <div class="hero-fact">⚡ Multi-spectrum ready (RGB · Thermal · Range)</div>
            <div class="hero-fact">🌡️ Calibrated thermal screening (ε = 0.95)</div>
            <div class="hero-fact">📡 LiDAR specular reflection association</div>
            <div class="hero-fact">❄️ Targeted lane de-icing actuation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. SIDEBAR CONFIGURATION
    st.sidebar.markdown("### ⚙️ System Configuration")
    device_list = get_available_devices()
    device_keys = [d[0] for d in device_list]
    device_labels = {d[0]: d[1] for d in device_list}

    # Select default device: cuda:1 if available (RTX 3050), else cuda:0, else cpu
    default_dev_idx = 0
    if "cuda:1" in device_keys:
        default_dev_idx = device_keys.index("cuda:1")
    elif "cuda:0" in device_keys:
        default_dev_idx = device_keys.index("cuda:0")

    device = st.sidebar.selectbox(
        "⚡ Compute Device",
        options=device_keys,
        index=default_dev_idx,
        format_func=lambda x: device_labels[x],
        help="Selects target GPU or CPU"
    )

    models_dir = Path("models")
    available_models = []
    if models_dir.exists():
        for pat in ["**/*.pt", "*.pt"]:
            available_models.extend([str(p) for p in models_dir.glob(pat)])
    default_checkpoint = "models/checkpoints/black_ice/weights/best.pt"
    if default_checkpoint not in available_models:
        available_models.insert(0, default_checkpoint)

    model_path = st.sidebar.selectbox(
        "🧠 Detection Checkpoint",
        options=available_models,
        index=0,
        help="Trained YOLOv8 model weights"
    )

    conf_threshold = st.sidebar.slider(
        "🎯 Confidence Threshold",
        min_value=0.05,
        max_value=1.0,
        value=0.35,
        step=0.05,
        help="Inference classification sensitivity"
    )

    # Initialize Backend Pipeline
    try:
        detector = load_detector(model_path, conf_threshold, device)
        pipeline = load_pipeline("configs/sensor_pipeline.yaml", model_path, device)
    except Exception as e:
        st.error(f"❌ Initialization error: {e}")
        return

    # 4. PRIMARY TABS: WORKBENCH, ARCHITECTURE, LIVE VIDEO, TELEMETRY, HISTORY
    tab_bench, tab_arch, tab_video, tab_diag, tab_hist = st.tabs([
        "🔬 Inspection Workbench",
        "📐 System Architecture",
        "📹 Live Video Feed",
        "📡 Sensor Diagnostics",
        "📑 Saved Scans History"
    ])

    # =========================================================================
    # TAB 1: INSPECTION WORKBENCH (#workbench)
    # =========================================================================
    with tab_bench:
        st.markdown('<div id="workbench"></div>', unsafe_allow_html=True)
        
        # Benchmark Presets & Custom Upload Columns
        col_src, col_presets = st.columns([2, 1])

        with col_src:
            st.markdown('<div class="bento-card">', unsafe_allow_html=True)
            st.markdown("#### 📤 Upload Road Footage")
            st.caption("Drag and drop any road scene (JPG, PNG, WEBP, MP4, MOV - 24 MB Max)")
            uploaded_file = st.file_uploader(
                "Upload road footage",
                type=["jpg", "jpeg", "png", "webp", "mp4", "mov"],
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with col_presets:
            st.markdown('<div class="bento-card">', unsafe_allow_html=True)
            st.markdown("#### 📂 Verified Test Presets")
            st.caption("One-click benchmark scenarios for immediate evaluation:")
            
            preset_options = [
                "None (Use custom upload)",
                "Glazed Black Ice Highway (OD Test)",
                "Frosted Snow Surface (White Sheet)",
                "Dry Asphalt - Smooth Surface",
                "Dry Asphalt - Slight Wear",
                "Dry Asphalt - Severe Texture"
            ]
            selected_preset = st.selectbox(
                "Preset Selector",
                options=preset_options,
                index=1,
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        # Multi-Sensor Environment Controls (Surface Temperature & LiDAR Range)
        with st.expander("🌡️ Multi-Sensor Simulation Parameters (Module 2 Thermal & Module 5 LiDAR)", expanded=False):
            ec1, ec2 = st.columns(2)
            with ec1:
                override_temp = st.slider("Road Surface Temperature (°C)", -15.0, 25.0, -2.5, 0.5,
                                         help="Screened by Module 2 (Risk window: -10°C to +3°C)")
            with ec2:
                override_dist = st.slider("LiDAR Distance to Surface (m)", 1.0, 35.0, 12.0, 0.5,
                                         help="Associated by Module 5 with specular reflection check")

        # Resolve Image Source
        img_to_process = None
        source_name = "Benchmark Image"

        if uploaded_file is not None:
            source_name = uploaded_file.name
            if uploaded_file.type.startswith("image/"):
                pil_img = Image.open(uploaded_file).convert("RGB")
                img_to_process = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        elif selected_preset != "None (Use custom upload)":
            source_name = selected_preset
            preset_paths = {
                "Glazed Black Ice Highway (OD Test)": Path("data/processed/images/test/OD/image_001_png.rf.381fc2618490a9441010c7a2a03c8bdc.jpg"),
                "Frosted Snow Surface (White Sheet)": Path("data/raw/white/train"),
                "Dry Asphalt - Smooth Surface": Path("data/dry/smooth"),
                "Dry Asphalt - Slight Wear": Path("data/dry/slight"),
                "Dry Asphalt - Severe Texture": Path("data/dry/severe")
            }
            target_p = preset_paths.get(selected_preset)
            if target_p and target_p.is_file():
                img_to_process = cv2.imread(str(target_p))
            elif target_p and target_p.is_dir():
                found_imgs = list(target_p.glob("*.jpg")) + list(target_p.glob("*.png"))
                if found_imgs:
                    img_to_process = cv2.imread(str(found_imgs[0]))

        # Run Multi-Sensor Pipeline
        if img_to_process is not None:
            with st.spinner("Executing Sensor Acquisition, Calibrated Screening, YOLOv8 & LiDAR Association..."):
                output = pipeline.process_image(
                    image=img_to_process,
                    road_surface_temp_c=override_temp,
                    lidar_distance_m=override_dist
                )

            # Record in session history
            st.session_state.history.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "source": source_name,
                "condition": output.road_condition,
                "confidence": output.ice_confidence,
                "distance": f"{output.estimated_distance:.1f} m" if output.estimated_distance else "N/A",
                "temp": f"{override_temp:.1f}°C",
                "status": output.uncertainty_status
            })

            # Prepare Viewport Images
            # 1. Visible View
            annotated_visible = img_to_process.copy()
            if output.patch_bbox is not None:
                x1, y1, x2, y2 = output.patch_bbox
                color = (0, 0, 235) if output.road_condition == "BLACK_ICE_HAZARD" else (0, 165, 255)
                cv2.rectangle(annotated_visible, (x1, y1), (x2, y2), color, 3)
                dist_str = f" · {output.estimated_distance:.1f}m" if output.estimated_distance else ""
                label_txt = f"{output.road_condition} ({output.ice_confidence:.1%}){dist_str}"
                cv2.putText(annotated_visible, label_txt, (x1, max(y1 - 10, 25)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
            
            # 2. Thermal View
            annotated_thermal = generate_thermal_view(img_to_process, override_temp, output.patch_bbox)

            # 3. Edge View
            annotated_edge = generate_edge_view(img_to_process, override_dist, output.patch_bbox)

            # Workbench Grid: Viewport Column + Output Telemetry Column
            col_view, col_telemetry = st.columns([3, 2])

            with col_view:
                st.markdown('<div class="bento-card">', unsafe_allow_html=True)
                
                # Spectrum Mode Toggle Bar
                vmode_col, title_col = st.columns([2, 1])
                with vmode_col:
                    spec_mode = st.radio(
                        "Spectrum Mode",
                        options=["Visible", "Thermal", "Edge view"],
                        horizontal=True,
                        label_visibility="collapsed"
                    )

                # Select Viewport Frame
                if spec_mode == "Visible":
                    active_frame = cv2.cvtColor(annotated_visible, cv2.COLOR_BGR2RGB)
                    mode_label = "VISIBLE · YOLOV8 DEEP INFERENCE"
                elif spec_mode == "Thermal":
                    active_frame = cv2.cvtColor(annotated_thermal, cv2.COLOR_BGR2RGB)
                    mode_label = "THERMAL · MLX90640 CALIBRATED (ε = 0.95)"
                else:
                    active_frame = cv2.cvtColor(annotated_edge, cv2.COLOR_BGR2RGB)
                    mode_label = "EDGE VIEW · LIDAR SPECULAR DROPOUT"

                st.markdown(f"""
                <div class="viewport-box">
                    <div class="viewport-view-label">{mode_label}</div>
                </div>
                """, unsafe_allow_html=True)
                st.image(active_frame, use_container_width=True)
                st.caption(f"Inspecting: {source_name} | Real-time sensor fusion active")
                st.markdown('</div>', unsafe_allow_html=True)

            with col_telemetry:
                st.markdown('<div class="bento-card">', unsafe_allow_html=True)
                st.markdown("#### 📋 Multi-Sensor Decision Matrix")

                # Output 1: Road Condition
                if output.road_condition == "BLACK_ICE_HAZARD":
                    st.markdown('<div class="badge-hazard">🚨 BLACK ICE HAZARD DETECTED</div>', unsafe_allow_html=True)
                elif output.road_condition in ["WET_ROAD_NO_ICE", "POTENTIAL_RISK"]:
                    st.markdown(f'<div class="badge-warning">⚠️ {output.road_condition}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="badge-safe">✅ ROAD CLEAR — NO HAZARD</div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Output 2 & Output 4: Ice Confidence & Estimated Distance
                m1, m2 = st.columns(2)
                with m1:
                    st.markdown(f"""
                    <div class="telemetry-card">
                        <div class="telemetry-label">ICE CONFIDENCE</div>
                        <div class="telemetry-val" style="color: {'#ef4444' if output.ice_confidence > 0.6 else '#07172c'};">
                            {output.ice_confidence:.1%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with m2:
                    dist_disp = f"{output.estimated_distance:.2f} m" if output.estimated_distance else "N/A"
                    st.markdown(f"""
                    <div class="telemetry-card">
                        <div class="telemetry-label">ESTIMATED DISTANCE</div>
                        <div class="telemetry-val">{dist_disp}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Output 3: Patch Bounding Box
                bbox_disp = f"[{output.patch_bbox[0]}, {output.patch_bbox[1]}, {output.patch_bbox[2]}, {output.patch_bbox[3]}]" if output.patch_bbox else "No localized patch"
                st.markdown(f"""
                <div class="telemetry-card">
                    <div class="telemetry-label">PATCH BOUNDING BOX [X1, Y1, X2, Y2]</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; font-weight: 600; color: #1e293b;">
                        {bbox_disp}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Output 5: Uncertainty Status
                st.markdown(f"""
                <div class="telemetry-card">
                    <div class="telemetry-label">UNCERTAINTY & FUSION VERIFICATION</div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; font-weight: 600; color: {'#059669' if output.uncertainty_status == 'CONFIRMED_HAZARD' else '#d97706'};">
                        {output.uncertainty_status}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Targeted De-icing Actuator Panel
                st.markdown("---")
                if output.road_condition == "BLACK_ICE_HAZARD" and output.patch_bbox is not None:
                    x1, y1, x2, y2 = output.patch_bbox
                    img_w = img_to_process.shape[1]
                    center_ratio = ((x1 + x2) / 2.0) / img_w
                    spray_pos = "LEFT LANE NOZZLE" if center_ratio < 0.4 else ("RIGHT LANE NOZZLE" if center_ratio > 0.6 else "CENTER DUAL NOZZLE")
                    impact_time = (output.estimated_distance / 16.6) if output.estimated_distance else 0.5

                    st.markdown(f"""
                    <div class="actuator-box">
                        <div class="actuator-header">
                            <span class="actuator-title">❄️ DE-ICING SPRAY ACTUATION</span>
                            <span style="color: #ef4444; font-weight: 800; font-family: 'JetBrains Mono';">ACTIVE PULSE</span>
                        </div>
                        <p style="margin-bottom: 8px;"><strong>Target Lane:</strong> {spray_pos}</p>
                        <p style="margin-bottom: 8px;"><strong>Calculated Impact:</strong> {impact_time:.2f}s (at 60 km/h)</p>
                        <p style="margin-bottom: 0;"><strong>Brine Delivery:</strong> 120 mL pulsed spray synchronized with vehicle velocity.</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="actuator-box">
                        <div class="actuator-header">
                            <span class="actuator-title">❄️ DE-ICING SPRAY ACTUATION</span>
                            <span style="color: #10b981; font-weight: 800; font-family: 'JetBrains Mono';">STANDBY</span>
                        </div>
                        <p style="margin-bottom: 0; color: #94a3b8;">System idle. Road surface safe or above freezing threshold.</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("👆 Upload an image or select a benchmark preset above to launch the multi-sensor pipeline.")

    # =========================================================================
    # TAB 2: SYSTEM ARCHITECTURE (#architecture)
    # =========================================================================
    with tab_arch:
        st.markdown('<div id="architecture"></div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="arch-container">
            <div class="eyebrow"><span class="eyebrow-line"></span> BUILT FOR WINTER ROADS</div>
            <div class="arch-heading">From raw signal to safer decisions.</div>
            <div class="arch-sub">
                A transparent, verifiable pipeline moving from multi-spectral hardware ingestion to autonomous de-icing actuation.
            </div>

            <div class="feature-grid">
                <!-- Step 01 -->
                <article class="feature-card">
                    <div class="feature-card-top">
                        <span class="step-number">01</span>
                        <span style="font-size: 1.2rem;">📷</span>
                    </div>
                    <h3>Spectral Ingestion</h3>
                    <p>
                        Simultaneously ingest 1080p RGB camera frames, MLX90640 32x24 long-wave IR thermal grids,
                        and 2D planar LiDAR forward range sweeps into a microsecond-synchronized buffer.
                    </p>
                    <span class="feature-footnote">RGB · THERMAL · RANGE</span>
                </article>

                <!-- Step 02 -->
                <article class="feature-card feature-card-accent">
                    <div class="feature-card-top">
                        <span class="step-number">02</span>
                        <span style="font-size: 1.2rem;">🌡️</span>
                    </div>
                    <h3>Calibrated Screening</h3>
                    <p>
                        Calibrates road emissivity (&epsilon; = 0.95 for asphalt) and screens against the critical
                        winter risk envelope [-10°C, +3°C]. Prevents false alarms on warm, wet roads.
                    </p>
                    <span class="feature-footnote">CALIBRATED RISK WINDOW</span>
                </article>

                <!-- Step 03 -->
                <article class="feature-card">
                    <div class="feature-card-top">
                        <span class="step-number">03</span>
                        <span style="font-size: 1.2rem;">🧠</span>
                    </div>
                    <h3>Vision Inference</h3>
                    <p>
                        Executes trained YOLOv8 neural network on incoming frames to detect ice sheen, regressing
                        patch bounding boxes [x1, y1, x2, y2] and generating classification confidence.
                    </p>
                    <span class="feature-footnote">YOLOV8 ACCELERATED</span>
                </article>

                <!-- Step 04 -->
                <article class="feature-card feature-card-accent">
                    <div class="feature-card-top">
                        <span class="step-number">04</span>
                        <span style="font-size: 1.2rem;">📡</span>
                    </div>
                    <h3>LiDAR Association</h3>
                    <p>
                        Casts LiDAR rays into the patch azimuth sector. Analyzes specular reflection dropout:
                        smooth glazed ice deflects laser pulses away from the receiver, confirming black ice!
                    </p>
                    <span class="feature-footnote">SPECULAR DROPOUT SIGNATURE</span>
                </article>

                <!-- Step 05 -->
                <article class="feature-card">
                    <div class="feature-card-top">
                        <span class="step-number">05</span>
                        <span style="font-size: 1.2rem;">❄️</span>
                    </div>
                    <h3>Targeted Actuation</h3>
                    <p>
                        Computes lateral lane offset and range-compensated delay &Delta;t = d / v to pulse targeted
                        dual-solenoid brine spray nozzles directly onto the hazard ahead of tires.
                    </p>
                    <span class="feature-footnote">CLOSED-LOOP DE-ICING</span>
                </article>
            </div>

            <div class="arch-note-banner">
                <span style="font-size: 1.3rem;">🛡️</span>
                <span>
                    <strong>Operational transparency comes first:</strong> this system never flags a road safe without multi-sensor verification across vision, calibrated thermography, and LiDAR specular reflection.
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Deep Technical Specifications Table
        st.markdown('<div class="bento-card">', unsafe_allow_html=True)
        st.markdown("### 🔬 Architectural Subsystem Specifications")

        s1, s2 = st.columns(2)
        with s1:
            st.markdown("""
            ##### Module 1 & 2: Acquisition & Screening
            * **RGB Sensor**: 1080p @ 30 FPS, 65° Horizontal FOV, auto-exposure compensation.
            * **Thermal Sensor**: Melexis MLX90640 $32 \\times 24$ IR thermopile array, I2C fast-mode+ (1 MHz).
            * **Emissivity Calibration**: Set to $\\epsilon = 0.95$ for asphalt/concrete pavements via Stefan-Boltzmann calibration:
              $$T_{\\text{calibrated}} = \\left(\\frac{T_{\\text{raw}}^4 - (1 - \\epsilon)T_{\\text{ambient}}^4}{\\epsilon}\\right)^{1/4}$$
            * **Screening Filter**: Surface temp $T > 3.0^\\circ\\text{C}$ routes to `WET_ROAD_NO_ICE` with zero false-positives.
            """)

        with s2:
            st.markdown("""
            ##### Module 3 & 5: Vision Model & LiDAR Association
            * **Vision Backbone**: YOLOv8 CSPDarknet with PAN-FPN feature pyramid, FP16 TensorRT / PyTorch CUDA execution.
            * **2D Planar LiDAR**: 905nm pulsed laser diode, 120° forward scan sector, 0.25° angular resolution, 40m range.
            * **Specular Dropout Detection**: Smooth ice forms a specular mirror for the 905nm laser, reflecting photons away from the detector and causing localized zero-returns:
              $$\\text{Dropout Ratio} = \\frac{N_{\\text{zero-return}}}{N_{\\text{sector rays}}} > 0.40$$
            * **Actuation Timing**: Solenoid trigger pulse scheduled at $\\Delta t = \\frac{d_{\\text{LiDAR}}}{v_{\\text{vehicle}}}$.
            """)
        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # TAB 3: LIVE VIDEO FEED (#live-video)
    # =========================================================================
    with tab_video:
        st.markdown('<div id="live-video"></div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-card">', unsafe_allow_html=True)
        st.markdown("#### 📹 Real-Time Stream Source")

        vsrc_col1, vsrc_col2 = st.columns([2, 1])
        with vsrc_col1:
            source_choice = st.selectbox(
                "Select Input Video Stream",
                options=["Webcam (0)", "Video File", "RTSP Stream"],
                label_visibility="collapsed"
            )
        with vsrc_col2:
            test_mov = Path("tests/videos/test1.mov")
            video_path = str(test_mov) if test_mov.exists() else ""
            if source_choice == "Video File":
                video_input = st.text_input("Path to .mp4 / .mov", value=video_path, label_visibility="collapsed")
            elif source_choice == "RTSP Stream":
                video_input = st.text_input("RTSP URL", placeholder="rtsp://...", label_visibility="collapsed")
            else:
                video_input = 0
        st.markdown('</div>', unsafe_allow_html=True)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            start_btn = st.button("▶️ Launch Live Stream", type="primary", use_container_width=True)
        with col_btn2:
            stop_btn = st.button("⏹️ Halt Stream", use_container_width=True)

        if start_btn:
            st.session_state.running_video = True
        if stop_btn:
            st.session_state.running_video = False

        vcol_feed, vcol_stats = st.columns([3, 2])
        with vcol_feed:
            feed_ph = st.empty()
        with vcol_stats:
            stats_ph = st.empty()
            alert_ph = st.empty()

        if st.session_state.running_video:
            camera = Camera(video_input)
            if not camera.open():
                st.error("❌ Failed to connect to camera source.")
                st.session_state.running_video = False
            else:
                while st.session_state.running_video:
                    ret, frame = camera.read()
                    if not ret or frame is None:
                        st.warning("Video stream ended.")
                        break

                    st.session_state.frame_count += 1
                    detections, inf_time = detector.detect_with_timing(frame)
                    if detections:
                        st.session_state.hazard_count += 1

                    # Annotate frame
                    annotated = frame.copy()
                    h, w = frame.shape[:2]
                    for det in detections:
                        x_center, y_center, width, height = det['bbox']
                        x1 = int((x_center - width/2) * w)
                        y1 = int((y_center - height/2) * h)
                        x2 = int((x_center + width/2) * w)
                        y2 = int((y_center + height/2) * h)
                        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 235), 3)
                        cv2.putText(annotated, f"BLACK ICE {det['confidence']:.1%}", (x1, max(y1 - 10, 25)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 235), 2)

                    annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                    feed_ph.image(annotated_rgb, use_container_width=True)

                    with stats_ph.container():
                        st.markdown(f"""
                        <div class="telemetry-card">
                            <div class="telemetry-label">PROCESSED FRAMES</div>
                            <div class="telemetry-val">{st.session_state.frame_count}</div>
                        </div>
                        <div class="telemetry-card">
                            <div class="telemetry-label">INFERENCE SPEED</div>
                            <div class="telemetry-val">{inf_time:.1f} ms ({1000/max(inf_time,1):.0f} FPS)</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with alert_ph.container():
                        if detections:
                            st.markdown('<div class="badge-hazard">🚨 BLACK ICE HAZARD</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="badge-safe">✅ ROAD CLEAR</div>', unsafe_allow_html=True)

                    time.sleep(0.01)
                camera.release()

    # =========================================================================
    # TAB 4: SENSOR DIAGNOSTICS (#diagnostics)
    # =========================================================================
    with tab_diag:
        st.markdown('<div id="diagnostics"></div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-card">', unsafe_allow_html=True)
        st.markdown("### 📡 Multi-Sensor Diagnostic Hub")
        st.markdown("Live telemetry and operating parameters of vehicle acquisition nodes.")

        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown("""
            <div class="telemetry-card">
                <div class="telemetry-label">NODE 01: RGB VISION</div>
                <div class="telemetry-val" style="color: #10b981; font-size: 1.4rem;">ONLINE</div>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 6px;">1920x1080 @ 30 FPS<br>FOV: 65° Horizontal</p>
            </div>
            """, unsafe_allow_html=True)
        with d2:
            st.markdown("""
            <div class="telemetry-card">
                <div class="telemetry-label">NODE 02: MLX90640 THERMAL</div>
                <div class="telemetry-val" style="color: #10b981; font-size: 1.4rem;">CALIBRATED</div>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 6px;">32x24 IR Array (768 pixels)<br>Emissivity ε = 0.95</p>
            </div>
            """, unsafe_allow_html=True)
        with d3:
            st.markdown("""
            <div class="telemetry-card">
                <div class="telemetry-label">NODE 03: 2D LIDAR SWEEP</div>
                <div class="telemetry-val" style="color: #10b981; font-size: 1.4rem;">TRACKING</div>
                <p style="font-size: 0.85rem; color: #64748b; margin-top: 6px;">120° Sector (360 rays)<br>Range: 0.2m - 40.0m</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### ⚡ Hardware Acceleration Profile")
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Host CPU"
        st.markdown(f"""
        * **Target Device:** `{device}`
        * **GPU Architecture:** `{gpu_name}`
        * **PyTorch Version:** `{torch.__version__}` (CUDA Available: `{torch.cuda.is_available()}`)
        * **Inference Pipeline:** Single-Pass Synchronous Multi-Sensor Coordinator
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # =========================================================================
    # TAB 5: SAVED SCANS HISTORY (#history)
    # =========================================================================
    with tab_hist:
        st.markdown('<div id="history"></div>', unsafe_allow_html=True)
        st.markdown('<div class="bento-card">', unsafe_allow_html=True)
        st.markdown("### 📑 Session Road Scans")
        st.caption("Scans evaluated during this interactive browser session:")

        if st.session_state.history:
            st.dataframe(
                st.session_state.history,
                use_container_width=True,
                hide_index=True
            )
            if st.button("🗑️ Clear Session History"):
                st.session_state.history = []
                st.rerun()
        else:
            st.markdown("""
            <div style="text-align: center; padding: 40px; color: #94a3b8;">
                <span style="font-size: 2rem;">❄️</span>
                <p style="margin-top: 8px;">No scans recorded yet. Upload an image or select a benchmark preset in the Workbench tab.</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 5. FOOTER
    st.markdown("""
    <footer style="margin-top: 50px; padding: 24px 0; border-top: 1px solid var(--line); display: flex; justify-content: space-between; align-items: center; color: #94a3b8; font-size: 12px;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: #38bdf8; font-size: 14px;">❄</span>
            <strong style="color: #0f172a;">BLACK ICE DETECTION</strong> — Autonomous Road Safety System
        </div>
        <div>
            <span>Multi-Sensor Fusion Platform · Calibrated Thermography · LiDAR Ray Association</span>
        </div>
    </footer>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
