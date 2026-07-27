from dataclasses import dataclass

from .features import Features


@dataclass
class DataFlowConfig:
    """
    Configuration for a data flow.

    Attributes:
        features (Features): The features to use for the data flow.
        uc_enabled (bool): Whether to use UC mode.
    """
    features: Features
    uc_enabled: bool = True
