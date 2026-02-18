from django.core.exceptions import ValidationError
from wagtail.admin.forms import WagtailAdminModelForm

from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid

import logging
import re

logger = logging.getLogger(__name__)

# ORCID format regex
ORCID_REGEX = re.compile(r'^(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])$')


def clean_orcid(orcid_input):
    """
    Clean and validate ORCID identifier.
    
    Args:
        orcid_input: Raw ORCID input (may include URL)
        
    Returns:
        Cleaned ORCID in format XXXX-XXXX-XXXX-XXXX
        
    Raises:
        ValidationError: If ORCID format is invalid
    """
    if not orcid_input:
        return None
    
    # Remove URL prefixes
    orcid = orcid_input.strip().replace('https://orcid.org/', '').replace('http://orcid.org/', '')
    
    # Validate format
    if not ORCID_REGEX.match(orcid):
        raise ValidationError(
            f"Invalid ORCID format: {orcid}. Expected format: 0000-0000-0000-0000"
        )
    
    return orcid


class EditorialboardForm(WagtailAdminModelForm):
    def clean(self):
        cleaned_data = super().clean()
        researcher = cleaned_data.get("researcher")
        
        # If researcher is not selected, require manual fields
        if not researcher:
            manual_given_names = cleaned_data.get("manual_given_names")
            manual_last_name = cleaned_data.get("manual_last_name")
            
            if not manual_given_names or not manual_last_name:
                raise ValidationError(
                    "Either select a researcher from the database or provide at least given names and last name."
                )
        
        return cleaned_data
    
    def _find_location(self, inst):
        """Find existing location from manual input fields."""
        # Guard: No location data provided
        if not (inst.manual_institution_city or inst.manual_institution_country):
            return None
        
        location_params = {}
        if inst.manual_institution_city:
            location_params['city_name__iexact'] = inst.manual_institution_city
        if inst.manual_institution_state:
            location_params['state_name__iexact'] = inst.manual_institution_state
        if inst.manual_institution_country:
            location_params['country_name__iexact'] = inst.manual_institution_country
        
        # Guard: No valid parameters
        if not location_params:
            return None
        
        try:
            location = Location.objects.filter(**location_params).first()
            if not location:
                logger.warning(
                    f"Location not found for: {location_params}. "
                    "Affiliation will not be created. Please add location manually."
                )
            return location
        except Exception as e:
            logger.error(f"Error finding location: {e}")
            return None
    
    def _create_affiliation(self, inst, location, user):
        """Create or update organization/affiliation."""
        # Guard: No institution name
        if not inst.manual_institution_name:
            return None
        
        # Guard: No location found
        if not location:
            logger.warning(
                f"Cannot create affiliation for {inst.manual_institution_name} "
                "because location was not found in database."
            )
            return None
        
        try:
            affiliation = Organization.create_or_update(
                name=inst.manual_institution_name,
                acronym=inst.manual_institution_acronym,
                location=location,
                user=user,
            )
            logger.info(f"Created/updated organization: {affiliation}")
            return affiliation
        except Exception as e:
            logger.error(f"Error creating organization: {e}")
            return None
    
    def _create_orcid(self, inst, user):
        """Create or get ORCID object."""
        # Guard: No ORCID provided
        if not inst.manual_orcid:
            return None
        
        try:
            orcid_cleaned = clean_orcid(inst.manual_orcid)
            orcid_obj, created = ResearcherOrcid.objects.get_or_create(
                orcid=orcid_cleaned,
                defaults={'creator': user}
            )
            if created:
                logger.info(f"Created ORCID: {orcid_cleaned}")
            return orcid_obj
        except ValidationError as e:
            logger.error(f"Invalid ORCID format: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating ORCID: {e}")
            return None
    
    def _add_researcher_identifier(self, researcher, source_name, identifier, user):
        """Add an identifier (Lattes or Email) to researcher."""
        # Guard: No identifier provided
        if not identifier or not researcher:
            return
        
        try:
            researcher_id, created = ResearcherIds.objects.get_or_create(
                researcher=researcher,
                source_name=source_name,
                identifier=identifier,
                defaults={'creator': user}
            )
            if created:
                logger.info(f"Added {source_name} ID: {identifier}")
        except Exception as e:
            logger.error(f"Error adding {source_name} ID: {e}")
    
    def _create_researcher_from_manual_fields(self, inst, user):
        """Create researcher and related records from manual input fields."""
        # Find or create affiliation
        location = self._find_location(inst)
        affiliation = self._create_affiliation(inst, location, user)
        
        # Create or get ORCID
        orcid_obj = self._create_orcid(inst, user)
        
        # Create or get researcher
        researcher = NewResearcher.get_or_create(
            user=user,
            given_names=inst.manual_given_names,
            last_name=inst.manual_last_name,
            suffix=inst.manual_suffix or '',
            affiliation=affiliation,
            orcid=orcid_obj,
        )
        logger.info(f"Created/updated researcher: {researcher}")
        
        # Add identifiers
        self._add_researcher_identifier(researcher, 'LATTES', inst.manual_lattes, user)
        self._add_researcher_identifier(researcher, 'EMAIL', inst.manual_email, user)
        
        return researcher
    
    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user

        # Guard: Researcher already selected or no manual fields
        if inst.researcher:
            self.save()
            return inst
        
        # Guard: Missing required manual fields
        if not (inst.manual_given_names and inst.manual_last_name):
            self.save()
            return inst
        
        # Process manual input fields to create/update researcher
        try:
            inst.researcher = self._create_researcher_from_manual_fields(inst, user)
        except Exception as e:
            logger.error(f"Error creating researcher from manual fields: {e}", exc_info=True)
            raise ValidationError(
                f"Error creating researcher from manual fields: {str(e)}"
            )

        self.save()
        return inst
