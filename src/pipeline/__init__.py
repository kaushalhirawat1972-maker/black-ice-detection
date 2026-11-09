"""
Pipeline package: End-to-end multi-sensor black ice detection pipeline.
"""

from src.pipeline.black_ice_pipeline import (
    BlackIcePipeline,
    PipelineOutput
)

__all__ = [
    "BlackIcePipeline",
    "PipelineOutput"
]
