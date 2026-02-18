# Editorial Board Form Improvements

## Overview

This document describes the improvements made to the editorial board member data entry functionality in the JournalProxyEditor administrative area.

## Problem Statement

Previously, users could only add editorial board members by selecting from existing researchers in the database using an autocomplete field. This created usability issues when:
- The researcher was not yet in the database
- Institution information was incomplete
- Identifiers (ORCID, Lattes, email) needed to be added

## Solution

We enhanced the `EditorialBoardMember` model and form to support dual input modes:

1. **Autocomplete Mode** (existing): Select researcher from database
2. **Manual Entry Mode** (new): Enter researcher details manually

### Features

#### 1. Manual Input Fields

New fields added to `EditorialBoardMember` model:

**Name Fields:**
- `manual_given_names` - Given names (e.g., "João")
- `manual_last_name` - Last name (e.g., "Silva")
- `manual_suffix` - Suffix (e.g., "Jr.", "Sr.", "III")

**Institution Fields:**
- `manual_institution_name` - Institution name (e.g., "Universidade de São Paulo")
- `manual_institution_acronym` - Institution acronym (e.g., "USP")
- `manual_institution_city` - City (e.g., "São Paulo")
- `manual_institution_state` - State/province (e.g., "São Paulo")
- `manual_institution_country` - Country (e.g., "Brasil")

**Identifier Fields:**
- `manual_orcid` - ORCID identifier (e.g., "0000-0001-2345-6789")
- `manual_lattes` - Lattes CV identifier
- `manual_email` - Email address

#### 2. Intelligent Form Processing

The `EditorialboardForm` handles both input modes:

- **Validation**: Requires either researcher selection OR manual name fields
- **ORCID Validation**: Validates ORCID format with regex pattern
- **Location Lookup**: Searches for matching locations using case-insensitive combined filters
- **Record Creation**: Automatically creates/updates:
  - `NewResearcher` record
  - `Organization` record (if location found)
  - `ResearcherOrcid` record
  - `ResearcherIds` records for Lattes and Email

#### 3. User Interface Improvements

- Fields organized into logical groups using `MultiFieldPanel`:
  - Manual Entry - Name
  - Manual Entry - Institution
  - Manual Entry - Identifiers
- Clear section headings
- Helpful tooltips for each field
- Improved visual hierarchy

#### 4. Error Handling & Logging

- Comprehensive logging for debugging
- Informative warning messages when location/affiliation cannot be created
- Proper `ValidationError` handling with detailed messages
- Graceful error recovery

## Usage

### For End Users

#### Adding a New Editorial Board Member

1. Navigate to Journal → Editorial Board tab
2. Click "Add Editorial Board Member"
3. Choose one of two options:

**Option A: Select Existing Researcher**
- Use the "Researcher" autocomplete field
- Start typing the researcher's name
- Select from dropdown

**Option B: Manual Entry**
- Leave "Researcher" field empty
- Fill in the manual entry fields:
  - At minimum: Given names and Last name
  - Optional: All other fields (institution, identifiers)
- Click "Save"

The system will automatically:
- Create a researcher record
- Link institution (if location exists in database)
- Add ORCID, Lattes, and Email identifiers

#### Important Notes

- **Location Requirement**: For institution affiliation to be created, the location (city + state + country) must already exist in the database
- **ORCID Format**: Must be in format `0000-0000-0000-0000` or include URL `https://orcid.org/0000-0000-0000-0000`
- **Priority**: If both researcher and manual fields are filled, the selected researcher takes priority

### For Developers

#### Running Tests

```bash
# Run all editorial board tests
python manage.py test editorialboard

# Run only form tests
python manage.py test editorialboard.tests.EditorialBoardMemberFormTest
```

#### Database Migration

```bash
# Apply migration
python manage.py migrate editorialboard
```

Migration file: `editorialboard/migrations/0011_add_manual_input_fields.py`

#### Code Structure

**Models:** `editorialboard/models.py`
- `EditorialBoardMember` - Main model with manual input fields

**Forms:** `editorialboard/forms.py`
- `EditorialboardForm` - Custom form with dual input logic
- `clean_orcid()` - ORCID validation helper

**Tests:** `editorialboard/tests.py`
- `EditorialBoardMemberFormTest` - Tests for manual input functionality

#### Key Methods

```python
def clean_orcid(orcid_input):
    """Clean and validate ORCID identifier"""
    
def clean(self):
    """Validate form: require either researcher OR manual fields"""
    
def save_all(self, user):
    """Save form and create related records from manual input"""
```

## Technical Details

### ORCID Validation

ORCID identifiers are validated using regex:
```python
ORCID_REGEX = re.compile(r'^(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])$')
```

Supports formats:
- `0000-0001-2345-6789`
- `https://orcid.org/0000-0001-2345-6789`
- `http://orcid.org/0000-0001-2345-6789`

### Location Matching

Location lookup uses case-insensitive matching on all provided fields:
```python
location_params = {
    'city_name__iexact': city,
    'state_name__iexact': state,
    'country_name__iexact': country,
}
location = Location.objects.filter(**location_params).first()
```

This ensures accurate matching by combining all location components.

### Record Creation Logic

When manual fields are provided:

1. **Find/Create Location** → Used for organization
2. **Create/Update Organization** → Requires location
3. **Create/Update ORCID** → If provided and valid
4. **Create/Update Researcher** → Links to organization and ORCID
5. **Add Lattes/Email IDs** → Linked to researcher

## Limitations

1. **Location Dependency**: Institution affiliation requires location to exist in database
2. **No Location Creation**: Form does not create new locations automatically
3. **Manual Field Priority**: Selected researcher overrides all manual fields

## Future Enhancements

Potential improvements:
- Add location creation from manual fields
- Support for institution divisions/departments
- Batch import functionality
- Enhanced ORCID integration (API lookup)
- Auto-fill from ORCID profile

## Security

- ✅ CodeQL scan completed - No vulnerabilities found
- ✅ Input validation for all fields
- ✅ ORCID format validation
- ✅ Proper error handling and logging

## References

- Issue: [Link to issue]
- PR: [Link to PR]
- Migration: `0011_add_manual_input_fields.py`
