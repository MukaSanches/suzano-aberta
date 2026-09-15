from suzano_aberta.api.schemas import PageInfo


def test_page_info_derives_navigation_metadata() -> None:
    first = PageInfo(total=12, limit=5, offset=0, next_offset=5)
    assert first.returned == 5
    assert first.has_more is True
    assert first.previous_offset is None

    middle = PageInfo(total=12, limit=5, offset=5, next_offset=10)
    assert middle.returned == 5
    assert middle.has_more is True
    assert middle.previous_offset == 0

    last = PageInfo(total=12, limit=5, offset=10, next_offset=None)
    assert last.returned == 2
    assert last.has_more is False
    assert last.previous_offset == 5
