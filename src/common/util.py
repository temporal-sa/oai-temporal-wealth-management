# Python's bool() function is stupid so we need to write our own
def str_to_bool(s) -> bool:
    s_lower = s.lower()
    if s_lower in ("true", "t", "yes", "y", "1"):
        return True
    elif s_lower in ("false", "f", "no", "n", "0"):
        return False
    else:
        raise ValueError(f"Cannot convert '{s}' to a bool")
