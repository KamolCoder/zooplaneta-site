from django.conf import settings


def site(request):
    return {"map_tile_url": settings.MAP_TILE_URL, "map_tile_attribution": settings.MAP_TILE_ATTRIBUTION}
