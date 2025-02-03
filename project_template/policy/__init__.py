"""Policy
"""
from .random import RandomPolicy
from .fixed import FixedGenerationPolicy


register_list = [RandomPolicy, FixedGenerationPolicy]