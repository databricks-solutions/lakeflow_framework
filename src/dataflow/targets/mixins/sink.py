"""Mixin for all sink-style targets."""
from __future__ import annotations

from typing import ClassVar

from dataflow.field import Field
from dataflow.target import TargetMeta


class SinkMixin(metaclass=TargetMeta):
    """
    Mixin that marks a :class:`~dataflow.target.Target` as a sink.

    Sets the two behavioural flags common to every sink, provides the
    ``target_name`` field (all sinks share ``"name"`` as their spec key),
    and exposes the backward-compat ``sink_name`` alias.

    Concrete sinks inherit from ``Target`` and ``SinkMixin`` and only need
    to declare their ``target_type`` and any additional spec fields::

        class MySink(Target, SinkMixin):
            target_type: ClassVar[str] = "my_sink"
            sinkOptions: dict = Field(default={})

            def create_target(self) -> None:
                ...
    """

    is_sink: ClassVar[bool] = True
    creates_before_flows: ClassVar[bool] = True

    # All sinks expose their name under the "name" spec key.
    target_name: str = Field(spec_field="name")

    @property
    def sink_name(self) -> str:
        """Alias for :attr:`target_name` (backward compatibility)."""
        return self.target_name
