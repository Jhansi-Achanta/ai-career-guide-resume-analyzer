"""JSON-file storage layer (the app's tiny "database").

No SQL server is needed - everything is stored in plain JSON files:

    data/analyses.json      saved resume analyses
    data/career_plans.json  saved AI career guidance plans

See ``storage/json_store.py`` for the generic file helpers and
``storage/records.py`` for the resume/career functions used by the routes.
"""
