import ipaddress


def resolve_client_ip(peer: str | None, forwarded_for: str | None, trusted_hops: int) -> str:
    """Best-effort client address behind `trusted_hops` reverse proxies that each append to X-Forwarded-For.

    A proxy appends the address it saw to the header, so entries on the right were written by
    infrastructure you control and entries on the left can be forged by the client. The address
    `trusted_hops` places from the right is the first one a trusted proxy recorded. If the header is
    missing, too short or malformed, fall back to the socket peer rather than trusting it.
    """
    peer = (peer or "unknown")[:45]
    if trusted_hops <= 0 or not forwarded_for:
        return peer
    parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
    if len(parts) < trusted_hops:
        return peer
    try:
        return str(ipaddress.ip_address(parts[-trusted_hops]))
    except ValueError:
        return peer
