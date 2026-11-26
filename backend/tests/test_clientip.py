from app.core.clientip import resolve_client_ip as resolve


def test_one_trusted_hop_uses_the_entry_the_proxy_appended_not_the_forged_one():
    # The client sent "6.6.6.6"; the proxy appended the address it actually saw.
    assert resolve("10.0.0.1", "6.6.6.6, 203.0.113.9", 1) == "203.0.113.9"


def test_two_hops_skip_the_second_proxy():
    assert resolve("10.0.0.1", "6.6.6.6, 203.0.113.9, 172.70.1.2", 2) == "203.0.113.9"


def test_zero_hops_ignores_the_header():
    assert resolve("10.0.0.1", "203.0.113.9", 0) == "10.0.0.1"


def test_missing_short_or_malformed_header_falls_back_to_the_socket_peer():
    assert resolve("10.0.0.1", None, 1) == "10.0.0.1"
    assert resolve("10.0.0.1", "", 1) == "10.0.0.1"
    assert resolve("10.0.0.1", "203.0.113.9", 2) == "10.0.0.1"
    assert resolve("10.0.0.1", "203.0.113.9, not-an-ip", 1) == "10.0.0.1"
    assert resolve(None, None, 1) == "unknown"


def test_ipv6_is_normalised_and_fits_the_column():
    ip = resolve("10.0.0.1", "2001:0db8:0000:0000:0000:0000:0000:0001", 1)
    assert ip == "2001:db8::1" and len(ip) <= 45
