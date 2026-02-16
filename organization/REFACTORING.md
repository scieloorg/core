# BaseOrganization Refactoring Documentation

## Overview

The `BaseOrganization` class has been refactored to improve code organization and reusability by separating concerns into focused mixin classes.

## Design Decisions

### 1. hasattr() check in BaseOrganization.__str__()
**Decision**: Use `hasattr()` to check for location field before accessing it.

**Rationale**: BaseOrganization is an abstract base class that may be inherited by multiple concrete implementations. While Organization includes a location field, future subclasses might not. The hasattr() check provides defensive programming and flexibility without breaking encapsulation.

**Alternative Considered**: Override `__str__()` in Organization. Rejected because it would require duplicating the logic in every subclass that includes location.

### 2. autocomplete_label() method in OrganizationNameMixin
**Decision**: Keep `autocomplete_label()` method that delegates to `__str__()`.

**Rationale**: This is a Wagtail framework convention. Wagtail's autocomplete functionality expects this method. It's used consistently across the entire codebase (see article, location, issue, etc. models). Removing it would break Wagtail integration.

**Pattern Usage**: This pattern appears in 20+ models throughout the codebase, confirming it's the expected approach.

## Changes Made

### 1. New Mixin Classes (in `core/models.py`)

#### OrganizationNameMixin
- **Purpose**: Provides organization identification fields
- **Fields**:
  - `name` (TextField): Organization's full name (required)
  - `acronym` (TextField): Organization's acronym (optional)
- **Features**:
  - Includes database indexes for both `name` and `acronym` fields
  - Provides `autocomplete_search_field` attribute set to "name"
  - Implements `autocomplete_label()` method for Wagtail autocomplete

#### VisualIdentityMixin
- **Purpose**: Provides visual identity and web presence fields
- **Fields**:
  - `url` (URLField): Organization's website URL (optional)
  - `logo` (ImageField): Organization's logo image (optional)
- **Features**:
  - Both fields are optional (blank=True, null=True)

### 2. Refactored BaseOrganization (in `organization/models.py`)

The `BaseOrganization` abstract model now:
- Inherits from `OrganizationNameMixin` and `VisualIdentityMixin`
- No longer directly defines `name`, `acronym`, `url`, or `logo` fields
- No longer includes the `location` field (moved to concrete implementations)
- Maintains all existing methods: `get()`, `create()`, `create_or_update()`, `update_logo()`, `update_url()`
- Updated `__str__()` method to handle optional location field

### 3. Updated Organization Model (in `organization/models.py`)

The concrete `Organization` model now:
- Explicitly defines the `location` field (previously inherited from BaseOrganization)
- Maintains `unique_together` constraint on (name, acronym, location)
- All other fields and behavior remain unchanged

## Benefits

1. **Separation of Concerns**: Different aspects of organization data (name/acronym, visual identity) are now in separate, focused mixins
2. **Reusability**: The new mixins can be used by other models that need organization name or visual identity fields
3. **Flexibility**: Models can choose which mixins to include based on their needs
4. **Maintainability**: Each mixin has a single, clear purpose making the code easier to understand and maintain
5. **Location Flexibility**: Removing location from BaseOrganization allows subclasses to define location fields with different requirements

## Backward Compatibility

✅ **No breaking changes** - All existing code continues to work:
- The `Organization` model still has all the same fields
- All methods (`get`, `create`, `create_or_update`) work exactly as before
- Database schema remains unchanged
- Existing tests continue to pass without modification

## Migration Notes

- **No database migration required**: The refactoring only changes how fields are inherited, not the actual database schema
- The `Organization` table structure remains identical to before
- All indexes and constraints are preserved

## Future Improvements

This refactoring enables:
- Other models to reuse `OrganizationNameMixin` for consistent organization naming
- Other models to reuse `VisualIdentityMixin` for branding fields
- Easy addition of new organization-related mixins (e.g., ContactInformationMixin)
- Better separation of concerns in organization-related models

## Testing

All existing tests in `organization/tests.py` continue to pass without modification, confirming backward compatibility.

## Usage Examples

### Using the Organization model (unchanged)
```python
from organization.models import Organization
from location.models import Location

# Create or update an organization (works exactly as before)
org = Organization.create_or_update(
    user=user,
    name="SciELO",
    acronym="SciELO",
    location=location,
    url="https://scielo.org",
    institution_type_mec="research",
    is_official=True
)

# Access fields (works exactly as before)
print(org.name)       # From OrganizationNameMixin
print(org.acronym)    # From OrganizationNameMixin
print(org.url)        # From VisualIdentityMixin
print(org.logo)       # From VisualIdentityMixin
print(org.location)   # From Organization model directly
```

### Using the mixins in new models (new capability)
```python
from core.models import OrganizationNameMixin, VisualIdentityMixin
from django.db import models

class Publisher(OrganizationNameMixin, models.Model):
    """Publisher only needs name and acronym, not visual identity."""
    # Automatically gets name and acronym fields
    founded_year = models.IntegerField()
    
    class Meta:
        # Will include indexes from OrganizationNameMixin
        pass

class Sponsor(OrganizationNameMixin, VisualIdentityMixin, models.Model):
    """Sponsor needs both name and visual identity."""
    # Automatically gets name, acronym, url, and logo fields
    sponsorship_level = models.CharField(max_length=50)
    
    class Meta:
        pass
```

## Related Files

- `core/models.py`: Contains new OrganizationNameMixin and VisualIdentityMixin
- `organization/models.py`: Contains refactored BaseOrganization and Organization
- `organization/tests.py`: Existing tests (no changes needed)
