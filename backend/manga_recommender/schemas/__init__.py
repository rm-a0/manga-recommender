"""Pydantic request and response models, one module per entity.

Each entity defines a `<Entity>Summary` for list items and embedding, and an
`<Entity>Detail` for the single-resource response. A schema lives in the module
of the entity whose data it carries, not the module of the endpoint that returns
it. The README's "Project structure" section records which shape may embed which.
"""
