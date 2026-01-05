"""
Módulo centralizado de métricas
Elimina duplicaciones y proporciona una fuente única de verdad para todas las métricas
"""

from .metrics_collector import MetricsCollector, SystemMetrics

__all__ = ['MetricsCollector', 'SystemMetrics']

