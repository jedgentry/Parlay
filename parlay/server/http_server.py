from twisted.web import server


FRESHNESS_TIME_SECS = 3600 # content younger than 1 hour is considered fresh


class CacheControlledSite(server.Site):
    """
    Overloading twisted.server.Site to add HTTP headers for enabling/disabling browser cache
    """
    def __init__(self, ui_caching, resource, requestFactory=None, *args, **kwargs):
        self._ui_caching = ui_caching
        server.Site.__init__(self, resource, requestFactory, *args, **kwargs)

    def getResourceFor(self, request):
        if not self._ui_caching:
            cache_strategy = "no-store, must-revalidate"
        else:
            cache_strategy = "max-age={}".format(FRESHNESS_TIME_SECS)

        request.setHeader("cache-control", cache_strategy)
        return server.Site.getResourceFor(self, request)
