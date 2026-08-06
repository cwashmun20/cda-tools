"""Results-source parsing for points_updating.

One module per results platform (O2CM, Ballroom Comp Express, CompOrganizer),
each producing CompetitionResult/DancerRef directly, plus the shared HTTP
infrastructure (http_client.py) all three need to fetch from live sites.
"""
