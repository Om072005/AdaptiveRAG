def normalize(text: str) -> str:
    """Unicode NFC and collapsed whitespace."""
    raise NotImplementedError


def doc_id(source: str, title: str) -> str:
    """First 16 hex of sha1(source + '|' + title)."""
    raise NotImplementedError
