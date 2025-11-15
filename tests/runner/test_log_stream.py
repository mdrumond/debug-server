from pathlib import Path

from debug_server.runner import LogChunk, LogStream


def test_log_stream_notifies_listeners(tmp_path: Path) -> None:
    stream_path = tmp_path / "logs" / "build.log"
    received: list[LogChunk] = []
    with LogStream(stream_path) as stream:
        stream.add_listener(received.append)
        stream.write("hello\n", stream="stdout")
        stream.write("oops\n", stream="stderr")
        subscription = stream.follow()
        stream.write("tail\n", stream="stdout")
        iterator = iter(subscription)
        chunk = next(iterator)
        assert chunk.text == "tail\n"
        subscription.close()
    assert stream_path.read_text() == "hello\noops\ntail\n"
    assert {chunk.stream for chunk in received} == {"stdout", "stderr"}
