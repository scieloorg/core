from .models import BaseOrgLevel
# variáveis globais
OrgLevelPublisher = None
OrgLevelOwner = None
OrgLevelCopyrightHolder = None
OrgLevelSponsor = None

def create_all():
    BaseOrgLevel.create_org_level_class("journal", "PublisherHistory")
    BaseOrgLevel.create_org_level_class("journal", "OwnerHistory")
    BaseOrgLevel.create_org_level_class("journal", "CopyrightHolderHistory")
    BaseOrgLevel.create_org_level_class("journal", "SponsorHistory")
