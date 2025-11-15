from rest_framework import serializers
from wagtail.models.sites import Site

from collection import models
from core.api.v1.serializers import LanguageSerializer
from core.utils.utils import get_url_file
from organization.api.v1.serializers import OrganizationSerializer


class CollectionNameSerializer(serializers.ModelSerializer):
    """Serializer para nomes traduzidos da coleção"""
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = models.CollectionName
        fields = [
            "text",
            "language",
        ]

class CollectionLogoListSerializer(serializers.ListSerializer):
    """
    Agrupa os logos por 'purpose' e consolida por idioma,
    eliminando duplicatas por (purpose, lang_code2).
    """
    def to_representation(self, data):
        items = super().to_representation(data)
        grouped = {}
        seen = set()

        for item in items:
            purpose = item.get("purpose")
            url = item.get("logo_url")
            lang = item.get("language", {})
            code2 = lang.get("code2")

            if not purpose or not code2 or not url:
                continue

            key = (purpose, code2)
            if key in seen:
                continue
            seen.add(key)

            grouped.setdefault(purpose, {}).update({code2: url})
        return grouped

class CollectionLogoSerializer(serializers.ModelSerializer):
    """Serializer para logos da coleção"""
    logo_url = serializers.SerializerMethodField()
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = models.CollectionLogo
        list_serializer_class = CollectionLogoListSerializer
        fields = [
            "logo_url",
            "purpose",
            "language",
        ]
    
    def get_logo_url(self, obj):
        if obj.logo:
            return get_url_file(obj.logo)
        return None


class SupportingOrganizationSerializer(serializers.ModelSerializer):
    """Serializer para organizações de suporte"""
    organization = OrganizationSerializer(read_only=True, many=False)
    
    class Meta:
        model = models.CollectionSupportingOrganization
        fields = [
            "organization",
            "initial_date",
            "final_date",

        ]


class ExecutingOrganizationSerializer(serializers.ModelSerializer):
    """Serializer para organizações executoras"""
    organization = OrganizationSerializer(read_only=True, many=False)
    
    class Meta:
        model = models.CollectionExecutingOrganization
        fields = [
            "organization",
            "initial_date",
            "final_date",
        ]


class SocialNetworkSerializer(serializers.ModelSerializer):
    """Serializer para redes sociais da coleção"""    
    class Meta:
        model = models.CollectionSocialNetwork
        fields = [
            "name",
            "url",
        ]


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer principal para Collection com todos os relacionamentos"""
    collection_names = CollectionNameSerializer(source='collection_name', many=True, read_only=True)
    logos = CollectionLogoSerializer(many=True, read_only=True)
    supporting_organizations = SupportingOrganizationSerializer(source='supporting_organization', many=True, read_only=True)
    executing_organizations = ExecutingOrganizationSerializer(source='executing_organization', many=True, read_only=True)
    social_networks = SocialNetworkSerializer(source='social_network', many=True, read_only=True)
    
    class Meta:
        model = models.Collection
        fields = [
            # Campos principais
            "acron3",
            "acron2",
            "code",
            "domain",
            "main_name",
            "status",
            "has_analytics",
            "collection_type",
            "is_active",
            "foundation_date",
            
            # Campos relacionados
            "collection_names",
            "logos",
            "supporting_organizations",
            "executing_organizations",
            "social_networks",
                        
            # Campos de controle (CommonControlField)
            "created",
            "updated",
        ]
        read_only_fields = ["created", "updated"]