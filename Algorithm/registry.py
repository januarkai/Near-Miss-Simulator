"""
Algorithm Registry.

Manages available near-miss detection algorithms.
"""

from typing import Dict, Type, List
from .base_algorithm import NearMissAlgorithm

class AlgorithmRegistry:
    _algorithms: Dict[str, Type[NearMissAlgorithm]] = {}
    
    @classmethod
    def register(cls, algorithm_cls: Type[NearMissAlgorithm]):
        """Register a new algorithm class."""
        try:
            name = algorithm_cls.get_name()
        except (AttributeError, NotImplementedError):
            name = algorithm_cls.__name__
             
        cls._algorithms[name] = algorithm_cls
        print(f"Registered algorithm: {name}")
        return algorithm_cls
        
    @classmethod
    def get_algorithm(cls, name: str) -> Type[NearMissAlgorithm]:
        """Get algorithm class by name."""
        return cls._algorithms.get(name)
    
    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List available algorithm names."""
        return list(cls._algorithms.keys())

# Global instance not strictly needed if using class methods, but good for pattern consistency
registry = AlgorithmRegistry()
