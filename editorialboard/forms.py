from django.core.exceptions import ValidationError
from wagtail.admin.forms import WagtailAdminModelForm

from location.models import Location
from organization.models import Organization
from researcher.models import NewResearcher, ResearcherIds, ResearcherOrcid


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
        if not inst.researcher and (inst.manual_given_names and inst.manual_last_name):
            # Create or get organization/affiliation if manual institution data is provided
            affiliation = None
            if inst.manual_institution_name:
                location = None
                if inst.manual_institution_city or inst.manual_institution_country:
                    # Try to find or create location
                    location_params = {}
                    if inst.manual_institution_city:
                        location_params['city_name'] = inst.manual_institution_city
                    if inst.manual_institution_state:
                        location_params['state_name'] = inst.manual_institution_state
                    if inst.manual_institution_country:
                        location_params['country_name'] = inst.manual_institution_country
                    
                    # Try to find existing location
                    if location_params:
                        try:
                            location = Location.objects.filter(**location_params).first()
                        except Exception:
                            pass
                
                # Create or get organization
                if location:
                    try:
                        affiliation = Organization.create_or_update(
                            name=inst.manual_institution_name,
                            acronym=inst.manual_institution_acronym,
                            location=location,
                            user=user,
                        )
                    except Exception:
                        # If location is required but not found, skip affiliation
                        pass
            
            # Create or get ORCID if provided
            orcid_obj = None
            if inst.manual_orcid:
                # Clean ORCID format
                orcid_cleaned = inst.manual_orcid.strip().replace('https://orcid.org/', '')
                try:
                    orcid_obj, _ = ResearcherOrcid.objects.get_or_create(
                        orcid=orcid_cleaned,
                        defaults={'creator': user}
                    )
                except Exception:
                    pass
            
            # Create or get researcher
            try:
                researcher = NewResearcher.get_or_create(
                    user=user,
                    given_names=inst.manual_given_names,
                    last_name=inst.manual_last_name,
                    suffix=inst.manual_suffix or '',
                    affiliation=affiliation,
                    orcid=orcid_obj,
                )
                inst.researcher = researcher
                
                # Add Lattes ID if provided
                if inst.manual_lattes and researcher:
                    try:
                        ResearcherIds.objects.get_or_create(
                            researcher=researcher,
                            source_name='LATTES',
                            identifier=inst.manual_lattes,
                            defaults={'creator': user}
                        )
                    except Exception:
                        pass
                
                # Add Email ID if provided
                if inst.manual_email and researcher:
                    try:
                        ResearcherIds.objects.get_or_create(
                            researcher=researcher,
                            source_name='EMAIL',
                            identifier=inst.manual_email,
                            defaults={'creator': user}
                        )
                    except Exception:
                        pass
                        
            except Exception as e:
                # Log error but continue with save
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating researcher from manual fields: {e}")

        self.save()

        return inst
