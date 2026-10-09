# Contributing

Provider interfaces live in `backend/app/domain/providers.py`. Keep their DTOs
independent of HTTP, persistence models and frontend types.

1. Add verification or geospatial implementations under the corresponding
   `backend/app/integrations/` directory.
2. Register a configuration name in the provider factory only once the module
   exists. Unsupported names must report an explicit error.
3. Preserve bounded scores, stable IDs, provider metadata and clear unavailable
   results. Providers do not mutate human-review status.
4. Run `pytest tests/test_provider_contracts.py` from `backend`, followed by the
   backend/frontend checks in the project README.
5. Explain API or schema changes in the pull request and include any required
   migration. Keep controlled fixtures visibly separate from real source data.

See [integration contracts](docs/integration_contracts.md) and
[data-source policy](docs/data_sources.md) for the maintained interfaces and
source/licence requirements.
