# Location Data Normalization - Status Field

## Overview

The location models (Country, State, City) now include a `status` field to track the processing state of location data. This implements a canonical data architecture that ensures data quality and traceability.

## Status Values

The `status` field can have one of the following values:

| Status | Description |
|--------|-------------|
| **RAW** | Raw data, no processing. Default value for new records. |
| **CLEANED** | Pre-cleaned data. HTML removed, spaces normalized. |
| **MATCHED** | Matched to a canonical record from reference databases. |
| **VERIFIED** | Officially validated against authoritative sources. |
| **REJECTED** | Invalid or unresolvable data that cannot be matched. |

## Data Cleaning

Each model now includes a `clean_data()` class method for pre-cleaning operations:

### City.clean_data(name)
Removes HTML tags and normalizes spaces in city names.

```python
cleaned_name = City.clean_data("<p>São Paulo</p>")
# Returns: "São Paulo"
```

### State.clean_data(name, acronym)
Removes HTML tags and normalizes spaces in state names and acronyms.

```python
cleaned_name, cleaned_acronym = State.clean_data("<b>São Paulo</b>", "<i>SP</i>")
# Returns: ("São Paulo", "SP")
```

### Country.clean_data(name, acronym, acron3)
Removes HTML tags and normalizes spaces in country names and acronyms.

```python
cleaned_name, cleaned_acronym, cleaned_acron3 = Country.clean_data(
    "<strong>Brazil</strong>", 
    "<em>BR</em>", 
    "<span>BRA</span>"
)
# Returns: ("Brazil", "BR", "BRA")
```

## Usage Example

### Creating records with status

```python
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

# Create a city with RAW status (default)
city = City.create(user=user, name="São Paulo")
# city.status == "RAW"

# Create a city with VERIFIED status
verified_city = City.create(user=user, name="Rio de Janeiro", status="VERIFIED")
# verified_city.status == "VERIFIED"
```

### Cleaning data before creation

```python
# Dirty data from external source
dirty_name = "<p>São Paulo   City</p>"

# Clean the data
cleaned_name = City.clean_data(dirty_name)
# cleaned_name == "São Paulo City"

# Create with CLEANED status
city = City.create(user=user, name=cleaned_name, status="CLEANED")
```

## Workflow

The typical workflow for location data is:

1. **RAW** → Data is initially created/imported in raw form
2. **CLEANED** → HTML is removed, spaces normalized
3. **MATCHED** → Data is matched to canonical reference (e.g., GeoNames)
4. **VERIFIED** → Data is validated against authoritative source
5. **REJECTED** → Data that cannot be verified or matched

## Database Migration

The status field was added via migration `0004_add_status_field.py`:
- Adds nullable `status` field to City, State, and Country models
- Default value is "RAW"
- Max length: 10 characters
- Choices: RAW, CLEANED, MATCHED, VERIFIED, REJECTED

## Testing

Comprehensive tests have been added to verify:
- Default status is RAW
- Status can be set to any valid value
- `clean_data()` methods remove HTML
- `clean_data()` methods normalize spaces
- `clean_data()` methods handle None values

Run tests with:
```bash
python manage.py test location
```

## Reference Data Sources

The canonical location data should be sourced from:

1. **Countries States Cities Database**
   - GitHub: https://github.com/dr5hn/countries-states-cities-database
   - Comprehensive database of countries, states, and cities

2. **GeoNames**
   - Website: https://www.geonames.org/
   - Official geographical database

## Future Enhancements

Potential improvements for the location normalization system:

1. Add methods to transition between states
2. Implement automatic matching against reference databases
3. Add validation rules for each status transition
4. Create admin views to bulk-update status
5. Add logging/audit trail for status changes
