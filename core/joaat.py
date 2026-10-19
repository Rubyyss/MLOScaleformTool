"""RAGE string hash (Jenkins one-at-a-time, lowercase)."""


def joaat(text: str) -> int:
    h = 0
    for b in text.lower().encode("utf-8"):
        h = (h + b) & 0xFFFFFFFF
        h = (h + (h << 10)) & 0xFFFFFFFF
        h ^= h >> 6
    h = (h + (h << 3)) & 0xFFFFFFFF
    h ^= h >> 11
    h = (h + (h << 15)) & 0xFFFFFFFF
    return h


def parse_hash(text: str) -> int:
    """Accept an MLO name, a decimal hash, 0x-hex, or 'int<hash>' / 'INT<hash>'."""
    t = text.strip()
    low = t.lower()
    if low.endswith(".gfx"):
        low = low[:-4]
    if low.startswith("int") and low[3:].isdigit():
        return int(low[3:]) & 0xFFFFFFFF
    if low.isdigit():
        return int(low) & 0xFFFFFFFF
    if low.startswith("0x"):
        try:
            return int(low, 16) & 0xFFFFFFFF
        except ValueError:
            pass
    if low.startswith("-") and low[1:].isdigit():
        return int(low) & 0xFFFFFFFF
    return joaat(t)
