from rest_framework import serializers
from collection import models
from core.api.v1.serializers import LanguageSerializer
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


class CollectionLogoSerializer(serializers.ModelSerializer):
    """Serializer para logos da coleção"""
    logo_url = serializers.SerializerMethodField()
    language = LanguageSerializer(many=False, read_only=True)

    class Meta:
        model = models.CollectionLogo
        fields = [
            "logo",
            "logo_url",
            "size",
            "language",
        ]
    
    def get_logo_url(self, obj):
        """Retorna a URL do logo renderizado no tamanho apropriado"""
        if obj.logo:
            # Ajusta o rendition baseado no tamanho
            rendition_specs = {
                'small': 'fill-100x100',
                'medium': 'fill-200x200',
                'large': 'fill-400x400',
                'banner': 'width-1200',
                'thumbnail': 'fill-150x150',
                'header': 'height-80',
                'footer': 'height-60',
            }
            spec = rendition_specs.get(obj.size, 'fill-200x200')
            rendition = obj.logo.get_rendition(spec)
            
            # Retorna URL completa se houver request no contexto
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(rendition.url)
            return rendition.url
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
    # Campos relacionados (read-only por padrão)
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