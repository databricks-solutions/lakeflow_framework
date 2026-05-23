from dataclasses import dataclass


@dataclass
class Features:
    """
    Features definition structure.

    Attributes:
        operationalMetadataEnabled (bool): Whether to enable the operational metadata feature.
    """
    operationalMetadataEnabled: bool = True

    def __post_init__(self):
        if self.operationalMetadataEnabled is None:
            self.operationalMetadataEnabled = True
