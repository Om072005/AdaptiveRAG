import pytest

from adaptiverag.telemetry.trace import ListenerStop, Trace


def test_a_failing_listener_does_not_stop_the_query() -> None:
    def broken(event: dict[str, object]) -> None:
        raise UnicodeEncodeError("charmap", "x", 0, 1, "no")

    t = Trace("q", "auto", "cli", broken)
    t.emit("embed", ms=1)
    t.delta("answer", "x")


def test_a_listener_can_stop_the_query() -> None:
    def stop(event: dict[str, object]) -> None:
        raise ListenerStop("page gone")

    with pytest.raises(ListenerStop):
        Trace("q", "auto", "cli", stop).emit("embed", ms=1)


def test_no_listener_means_no_events_and_no_cost() -> None:
    Trace("q", "auto", "cli").emit("embed", ms=1)
