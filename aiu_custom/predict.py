"""
aiu_custom/predict.py - 서빙 진입점 (re-export)
custom_server.py 가 일관된 경로(aiu_custom.predict.ModelWrapper)로 모델을 찾도록 한다.
"""

from .model_wrapper import ModelWrapper

__all__ = ["ModelWrapper"]
