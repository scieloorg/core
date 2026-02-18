from django.core.exceptions import ValidationError
from wagtail.admin.forms import WagtailAdminModelForm

from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid

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
                    "Either select a researcher from the database or provide at least given names and last name."
                )
        
        return cleaned_data
    
    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user

        # Process manual input fields to create/update researcher
        # Only process manual fields if no researcher is selected
        if not inst.researcher and (inst.manual_given_names and inst.manual_last_name):
            try:
                # Create or get organization/affiliation if manual institution data is provided
                affiliation = None
                if inst.manual_institution_name:
                    location = None
                    if inst.manual_institution_city or inst.manual_institution_country:
                        # Try to find existing location
                        location_params = {}
                        if inst.manual_institution_city:
                            location_params['city_name__iexact'] = inst.manual_institution_city
                        if inst.manual_institution_state:
                            location_params['state_name__iexact'] = inst.manual_institution_state
                        if inst.manual_institution_country:
                            location_params['country_name__iexact'] = inst.manual_institution_country
                        
                        if location_params:
                            try:
                                location = Location.objects.filter(**location_params).first()
                                if not location:
                                    logger.warning(
                                        f"Location not found for: {location_params}. "
                                        "Affiliation will not be created. Please add location manually."
                                    )
                            except Exception as e:
                                logger.error(f"Error finding location: {e}")
                    
                    # Create or get organization only if we have a location
                    if location:
                        try:
                            affiliation = Organization.create_or_update(
                                name=inst.manual_institution_name,
                                acronym=inst.manual_institution_acronym,
                                location=location,
                                user=user,
                            )
                            logger.info(f"Created/updated organization: {affiliation}")
                        except Exception as e:
                            logger.error(f"Error creating organization: {e}")
                    else:
                        logger.warning(
                            f"Cannot create affiliation for {inst.manual_institution_name} "
                            "because location was not found in database."
                        )
                
                # Create or get ORCID if provided
                orcid_obj = None
                if inst.manual_orcid:
                    # Clean ORCID format
                    orcid_cleaned = inst.manual_orcid.strip().replace('https://orcid.org/', '').replace('http://orcid.org/', '')
                    try:
                        orcid_obj, created = ResearcherOrcid.objects.get_or_create(
                            orcid=orcid_cleaned,
                            defaults={'creator': user}
                        )
                        if created:
                            logger.info(f"Created ORCID: {orcid_cleaned}")
                    except Exception as e:
                        logger.error(f"Error creating ORCID {orcid_cleaned}: {e}")
                
                # Create or get researcher
                researcher = NewResearcher.get_or_create(
                    user=user,
                    given_names=inst.manual_given_names,
                    last_name=inst.manual_last_name,
                    suffix=inst.manual_suffix or '',
                    affiliation=affiliation,
                    orcid=orcid_obj,
                )
                inst.researcher = researcher
                logger.info(f"Created/updated researcher: {researcher}")
                
                # Add Lattes ID if provided
                if inst.manual_lattes and researcher:
                    try:
                        lattes_id, created = ResearcherIds.objects.get_or_create(
                            researcher=researcher,
                            source_name='LATTES',
                            identifier=inst.manual_lattes,
                            defaults={'creator': user}
                        )
                        if created:
                            logger.info(f"Added Lattes ID: {inst.manual_lattes}")
                    except Exception as e:
                        logger.error(f"Error adding Lattes ID: {e}")
                
                # Add Email ID if provided
                if inst.manual_email and researcher:
                    try:
                        email_id, created = ResearcherIds.objects.get_or_create(
                            researcher=researcher,
                            source_name='EMAIL',
                            identifier=inst.manual_email,
                            defaults={'creator': user}
                        )
                        if created:
                            logger.info(f"Added Email ID: {inst.manual_email}")
                    except Exception as e:
                        logger.error(f"Error adding Email ID: {e}")
                        
            except Exception as e:
                # Log error but continue with save
                logger.error(f"Error creating researcher from manual fields: {e}", exc_info=True)
                raise ValidationError(
                    f"Error creating researcher from manual fields: {str(e)}"
                )

        self.save()

        return inst
