from rest_framework import serializers
from collection import models


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
            "id",
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


class CollectionNameSerializer(serializers.ModelSerializer):
    """Serializer para nomes traduzidos da coleção"""
    class Meta:
        model = models.CollectionName
        fields = [
            "id",
            "name",
            "language",
            "is_primary",
        ]


class CollectionLogoSerializer(serializers.ModelSerializer):
    """Serializer para logos da coleção"""
    logo_url = serializers.SerializerMethodField()
    size_display = serializers.CharField(source='get_size_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    
    class Meta:
        model = models.CollectionLogo
        fields = [
            "id",
            "logo",
            "logo_url",
            "size",
            "size_display",
            "language",
            "language_display",
            "description",
            "is_primary",
            "sort_order",
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


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer básico para organizações"""
    class Meta:
        model = models.Organization
        fields = [
            "name",
            "acronym",
            "country",
            "state",
            "city",
            "address",
            "zip_code",
            "phone",
            "email",
            "website",
        ]


class SupportingOrganizationSerializer(serializers.ModelSerializer):
    """Serializer para organizações de suporte"""
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = models.CollectionSupportingOrganization
        fields = [
            "organization",
            "role",
            "start_date",
            "end_date",
            "is_active",
            "sort_order",
        ]


class ExecutingOrganizationSerializer(serializers.ModelSerializer):
    """Serializer para organizações executoras"""
    organization = OrganizationSerializer(read_only=True)
    
    class Meta:
        model = models.CollectionExecutingOrganization
        fields = [
            "organization",
            "role",
            "start_date",
            "end_date",
            "is_active",
            "sort_order",
        ]


class SocialNetworkSerializer(serializers.ModelSerializer):
    """Serializer para redes sociais da coleção"""    
    class Meta:
        model = models.CollectionSocialNetwork  # Assumindo que é este o nome do modelo
        fields = [
            "name",
            "url",
            "sort_order",
        ]


class CollectionListSerializer(serializers.ModelSerializer):    
    class Meta:
        model = models.Collection
        fields = [
            "id",
            "acron3",
            "acron2",
            "code",
            "main_name",
            "status",
            "collection_type",
            "is_active",
            "primary_logo_url",
        ]

