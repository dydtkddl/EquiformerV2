# Changelog

All notable changes to SurfScreen will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Phase 11 Testing & Security**
  - Comprehensive unit tests for Phase 11 modules (cache, batch, scheduler, auth, notifications)
  - API integration tests for all new endpoints
  - Security middleware: API Key authentication, JWT support, RBAC
  - Rate limiting middleware with token bucket and sliding window algorithms
  - Security documentation guide

- Phase 11: Advanced Features (v1.1)
  - **Result Caching**
    - Redis-based cache manager with graceful degradation
    - `@cache_result` and `@invalidate_cache` decorators
    - Cache API endpoints (stats, keys, clear)
  - **Batch Processing**
    - Parallel execution with ThreadPoolExecutor
    - Checkpointing and resume support
    - Retry logic with exponential backoff
    - Batch API endpoints (submit, list, results, download)
  - **Job Scheduling**
    - APScheduler integration for cron/interval/once/dependency
    - Schedule API endpoints (CRUD, pause/resume, trigger)
  - **User Management**
    - Users, Teams, and Quota models
    - API key authentication with SHA256 hashing
    - Users API endpoints (CRUD, API keys, quota)
  - **Notification System**
    - Webhook client with HMAC signatures
    - Multi-channel support (webhook, email, websocket)
    - Webhooks API endpoints (CRUD, test, deliveries)
  - **Dashboard Updates**
    - Batch management page
    - Schedules management page

- Phase 9: Integration Testing
  - API workflow tests
  - API authentication tests
  - Dashboard E2E tests with Playwright
  - CI/CD pipeline with GitHub Actions
- Phase 10: Docker & Documentation
  - Dockerfile for API and Dashboard
  - docker-compose for production and development
  - Deployment guide
  - User guide
  - Developer guide

## [0.9.0] - 2026-02-02

### Added

- Phase 8: Scientific Validation
  - Reference data module with experimental/DFT values
  - Unit conversion utilities (eV, kJ/mol, Hartree, etc.)
  - Physics validation functions
    - Adsorption energy validation
    - MD energy conservation check
    - Temperature stability validation
    - Boltzmann distribution check
    - Force convergence validation
  - Validation reporter (JSON, Markdown, HTML)
  - CLI `surfscreen validate` command
  - Benchmark tests for MACE/xTB

## [0.8.0] - 2026-01-30

### Added

- Phase 7: Web Dashboard
  - Next.js 16 with TypeScript
  - Dashboard home with stats
  - Jobs management page
  - Screening job creation
  - MD simulation job creation
  - Settings page
  - Dark/Light theme support
  - Real-time job polling

### Changed

- API endpoints for dashboard integration

## [0.7.0] - 2026-01-25

### Added

- Phase 6: REST API Layer
  - FastAPI application
  - Job management endpoints
  - Screening endpoints
  - MD simulation endpoints
  - API key authentication
  - CORS support
  - OpenAPI documentation
  - CLI `surfscreen api` commands

## [0.6.0] - 2026-01-20

### Added

- Interactive HTML reports
- Enhanced logging system
- Report templates

## [0.5.0] - 2026-01-15

### Added

- MD simulation engine
  - NVT ensemble (Langevin, Nosé-Hoover)
  - NVE ensemble
  - Trajectory output
  - Analysis tools (MSD, RDF, diffusion)

## [0.4.0] - 2026-01-10

### Added

- Surface adsorption screening
  - Random configuration generation
  - Site-based placement
  - Energy ranking

## [0.3.0] - 2026-01-05

### Added

- Calculator abstraction layer
  - EMT calculator
  - MACE calculator
  - xTB calculator
- Geometry optimization

## [0.2.0] - 2025-12-28

### Added

- Surface module
  - FCC surface generation
  - Supercell creation
  - Vacuum layer handling

## [0.1.0] - 2025-12-20

### Added

- Initial release
- Molecule handling
  - XYZ file I/O
  - Conformer generation
  - SMILES to 3D conversion
- CLI structure
- Basic logging

---

[Unreleased]: https://github.com/your-org/surfscreen/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/your-org/surfscreen/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/your-org/surfscreen/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/your-org/surfscreen/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/your-org/surfscreen/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/your-org/surfscreen/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/your-org/surfscreen/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/your-org/surfscreen/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/your-org/surfscreen/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-org/surfscreen/releases/tag/v0.1.0
