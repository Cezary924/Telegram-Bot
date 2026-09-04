separator = ":"
max_length = 64


def build(module_name: str, action: str, *arguments: str | int) -> str:
    data = separator.join([module_name, action, *[str(argument) for argument in arguments]])
    if len(data.encode('utf8')) > max_length:
        raise ValueError("Callback data longer than " + str(max_length) + " bytes: " + data)
    return data


def parse(data: str) -> tuple[str, str, list[str]]:
    parts = data.split(separator)
    if len(parts) < 2:
        raise ValueError("Malformed callback data: " + data)
    return parts[0], parts[1], parts[2:]


def room_for_arguments(module_name: str, action: str) -> int:
    used = (module_name + separator + action + separator).encode('utf8')
    return max_length - len(used)
