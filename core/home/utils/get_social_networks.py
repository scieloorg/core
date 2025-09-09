from collection.models import CollectionSocialNetwork

def get_social_networks(collection_acron3):
    return CollectionSocialNetwork.objects.filter(page__acron3=collection_acron3)