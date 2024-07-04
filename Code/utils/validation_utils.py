def validate_version_tag(tag):
    # Remove the "v" if it exists
    if tag.lower().startswith("v"):
        tag = tag[1:]

    # Split the tag into numbers using dots as separators
    numbers = tag.split(".")

    # Check if the tag has exactly 3 numbers
    if len(numbers) != 3:
        return False

    # Check if each number is a valid integer
    for number in numbers:
        if not number.isdigit():
            return False

    return True
