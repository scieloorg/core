from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminModelForm

from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid
from researcher.utils import clean_orcid

import logging

logger = logging.getLogger(__name__)


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
                    _("Either select a researcher from the database or provide at least given names and last name.")
                )
        
        return cleaned_data
    
    def _find_location(self, inst, user):
        """Find existing location from manual input fields using Location model."""
        # Guard: No location data provided
        if not (inst.manual_institution_city or inst.manual_institution_state or inst.manual_institution_country):
            return None
        
        try:
            # Try to find/create location using Location.create_or_update
            # Country is now a ForeignKey, so we use the object directly
            location = Location.create_or_update(
                user=user,
                country=inst.manual_institution_country,  # Use the Country object directly
                country_name=inst.manual_institution_country.name if inst.manual_institution_country else None,
                country_acron3=inst.manual_institution_country.acron3 if inst.manual_institution_country else None,
                country_acronym=inst.manual_institution_country.acronym if inst.manual_institution_country else None,
                country_text=None,
                state=None,
                state_name=inst.manual_institution_state,
                state_acronym=None,
                state_text=None,
                city=None,
                city_name=inst.manual_institution_city,
                lang=None,
            )
            
            if location:
                logger.info(f"Found/created location: {location}")
                return location
            
            logger.warning(
                f"Location not found for: city={inst.manual_institution_city}, "
                f"state={inst.manual_institution_state}, country={inst.manual_institution_country}. "
                "Affiliation will not be created. Please add location manually."
            )
            return None
        except Exception as e:
            logger.error(f"Error finding/creating location: {e}")
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
    
    def _create_researcher_from_manual_fields(self, inst, user):
        """Create researcher and related records from manual input fields."""
        # Find or create affiliation
        location = self._find_location(inst, user)
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
        
        # Add identifiers using instance methods
        if inst.manual_lattes:
            researcher.add_lattes_id(inst.manual_lattes, user)
        
        if inst.manual_email:
            researcher.add_email(inst.manual_email, user)
        
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
                _("Error creating researcher from manual fields: %(error)s") % {'error': str(e)}
            )

        self.save()
        return inst
