def first_repeated_char(str1):
    seen = set()
    for char in str1:
        if char in seen:
            return char
        seen.add(char)
    return None

# Example usage:
print(first_repeated_char("programming"))  # Output: 'r'
print(first_repeated_char("abcdefg"))     # Output: None