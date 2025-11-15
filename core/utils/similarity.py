from difflib import SequenceMatcher


def is_similar(str1, str2, min_ratio=0.7):
    return SequenceMatcher(None, str1, str2).ratio() > min_ratio


def how_similar(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()
