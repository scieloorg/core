import re
from datetime import datetime, timedelta


def get_date_range(from_date=None, until_date=None, days_to_go_back=7):
    """
    Extract a date range from the provided parameters.

    Args:
        from_date (str): The start date in the format 'YYYY-MM-DD'.
        until_date (str): The end date in the format 'YYYY-MM-DD'.
        days_to_go_back (int): The number of days to go back from the current date.

    Returns:
        tuple: A tuple containing the start date and end date in the format 'YYYY-MM-DD'.
    """
    now = datetime.now()

    # Validate date formats
    if from_date and not re.match(r"\d{4}-\d{2}-\d{2}", from_date):
        raise ValueError("Invalid from_date format. Expected format: YYYY-MM-DD")

    if until_date and not re.match(r"\d{4}-\d{2}-\d{2}", until_date):
        raise ValueError("Invalid until_date format. Expected format: YYYY-MM-DD")

    # Set defaults based on what's provided
    if not from_date and not until_date:
        from_date = (now - timedelta(days=days_to_go_back)).strftime("%Y-%m-%d")
        until_date = now.strftime("%Y-%m-%d")

    elif not from_date:
        # Only until_date provided
        from_date = (now - timedelta(days=days_to_go_back)).strftime("%Y-%m-%d")

    elif not until_date:
        # Only from_date provided
        until_date = now.strftime("%Y-%m-%d")

    # Override with days_to_go_back if specified
    if days_to_go_back:
        from_date = (now - timedelta(days=int(days_to_go_back))).strftime("%Y-%m-%d")
        until_date = now.strftime("%Y-%m-%d")

    return from_date, until_date
