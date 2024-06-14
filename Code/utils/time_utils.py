def time_str_to_minutes(time: str) -> int:
    if time == "":
        return 0

    time = time.replace("d", " ").replace("h", " ").replace("min", " ").split()
    time = [int(t) for t in time]

    if len(time) == 1:
        return time[0]
    elif len(time) == 2:
        return time[0] * 60 + time[1]
    elif len(time) == 3:
        return time[0] * 24 * 60 + time[1] * 60 + time[2]
    else:
        raise ValueError("Invalid time string")
