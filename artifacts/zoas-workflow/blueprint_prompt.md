# Mentrix Lattice structural blueprint
**Project key:** zinnia-zoas
**Workspace:** C:\Users\karuppk\zect-workspaces\zinnia\zoas
**Commit:** aec1f4ac12b87ec5d8b3b1c752b07972a9102970
**Tech stack:** javascript, python, typescript

## Stats
- files=393 symbols=6174 functions=5063 classes=788 endpoints=234 call_edges=4672 docs=382 wikilinks=303

## God nodes (highest connectivity)
- file swagger-ui-bundle.js @ zinnia-modern/frontend/public/swagger-ui/swagger-ui-bundle.js (degree=4995)
- file swagger-ui-standalone-preset.js @ zinnia-modern/frontend/public/swagger-ui/swagger-ui-standalone-preset.js (degree=1274)
- file api.ts @ zinnia-modern/frontend/lib/api.ts (degree=314)
- folder zinnia-modern @ __dir__zinnia-modern (degree=216)
- file APIWizard.tsx @ zinnia-modern/frontend/components/api-builder/APIWizard.tsx (degree=134)
- file admin_monitoring.py @ zinnia-modern/backend/app/routers/admin_monitoring.py (degree=132)
- file builder.py @ zinnia-modern/backend/app/routers/builder.py (degree=124)
- file roleUtils.ts @ zinnia-modern/frontend/lib/utils/roleUtils.ts (degree=96)
- class AIService @ zinnia-modern/backend/app/services/ai_service.py (degree=92)
- file documents.py @ zinnia-modern/backend/app/routers/documents.py (degree=86)
- file page.tsx @ zinnia-modern/frontend/app/dashboard/document-generation/page.tsx (degree=83)
- vault zoas @ __vault__ (degree=74)

## API endpoints
- GET /api/proxy-download — zinnia-modern/backend/main.py
- POST /api/proxy-download/generated-text — zinnia-modern/backend/main.py
- GET /docs — zinnia-modern/backend/main.py
- GET /openapi-vendor.json — zinnia-modern/backend/main.py
- GET /openapi-inhouse.json — zinnia-modern/backend/main.py
- GET /docs-vendor — zinnia-modern/backend/main.py
- GET / — zinnia-modern/backend/main.py
- GET /users — zinnia-modern/backend/app/database.py
- GET /endpoint — zinnia-modern/backend/app/core/permissions.py
- GET /resource/{resource_id} — zinnia-modern/backend/app/core/permissions.py
- POST /admin/deploy — zinnia-modern/backend/app/routers/admin.py
- GET /admin/deploy/status — zinnia-modern/backend/app/routers/admin.py
- GET /admin/deploy/logs — zinnia-modern/backend/app/routers/admin.py
- POST /admin/deploy/cancel — zinnia-modern/backend/app/routers/admin.py
- POST /admin/deploy/github — zinnia-modern/backend/app/routers/admin.py
- GET /admin/deploy/health — zinnia-modern/backend/app/routers/admin.py
- POST /admin/email-outbox/retry — zinnia-modern/backend/app/routers/admin.py
- GET /admin/email-outbox/health — zinnia-modern/backend/app/routers/admin.py
- GET /admin/monitoring/overview — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/health — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/api-logs — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/user-activity — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/errors — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/system-info — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/overview — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/by-user — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/by-feature — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/by-model — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/failures — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/trends — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/top-users — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-usage/export — zinnia-modern/backend/app/routers/admin_monitoring.py
- PATCH /admin/monitoring/ai-usage/{log_id}/outcome — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-access/users — zinnia-modern/backend/app/routers/admin_monitoring.py
- PUT /admin/monitoring/ai-access/users/{user_id} — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-access/roles — zinnia-modern/backend/app/routers/admin_monitoring.py
- PUT /admin/monitoring/ai-access/roles/{role_id} — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/ai-access/features — zinnia-modern/backend/app/routers/admin_monitoring.py
- PUT /admin/monitoring/ai-access/features/{feature_id} — zinnia-modern/backend/app/routers/admin_monitoring.py
- GET /admin/monitoring/documents/overview — zinnia-modern/backend/app/routers/admin_monitoring.py

## Key classes
- const — test-swagger-ui.js
- BuildAPIBrowserTester — archive/old-tests/test_build_api_browser.py
- BuildAPITester — archive/old-tests/test_build_api_functionality.py
- OpenAPIFilterMiddleware — zinnia-modern/backend/main.py
- AIUserSetting — zinnia-modern/backend/app/models/ai_access_control.py
- AIRoleDefault — zinnia-modern/backend/app/models/ai_access_control.py
- AIFeatureConfig — zinnia-modern/backend/app/models/ai_access_control.py
- AIUsageLog — zinnia-modern/backend/app/models/ai_usage.py
- Announcement — zinnia-modern/backend/app/models/announcement.py
- APICategory — zinnia-modern/backend/app/models/api.py
- API — zinnia-modern/backend/app/models/api.py
- Endpoint — zinnia-modern/backend/app/models/api.py
- APIVersion — zinnia-modern/backend/app/models/api.py
- Schema — zinnia-modern/backend/app/models/api.py
- Documentation — zinnia-modern/backend/app/models/api.py
- EndpointDocument — zinnia-modern/backend/app/models/api.py
- DownloadToken — zinnia-modern/backend/app/models/api.py
- AuditLog — zinnia-modern/backend/app/models/audit.py
- APIMetric — zinnia-modern/backend/app/models/audit.py
- RateLimitHit — zinnia-modern/backend/app/models/audit.py
- SIDSession — zinnia-modern/backend/app/models/audit.py
- APIKey — zinnia-modern/backend/app/models/audit.py
- AuthToken — zinnia-modern/backend/app/models/auth_token.py
- EmailOutbox — zinnia-modern/backend/app/models/email_outbox.py
- FeatureRoleAccess — zinnia-modern/backend/app/models/feature_access_control.py
- Company — zinnia-modern/backend/app/models/organization.py
- Capability — zinnia-modern/backend/app/models/organization.py
- Project — zinnia-modern/backend/app/models/organization.py
- Permission — zinnia-modern/backend/app/models/permission.py
- UserAPIAccess — zinnia-modern/backend/app/models/permission.py

## Key functions
- testSwaggerUI — test-swagger-ui.js
- check_schema — archive/backend-diagnostics/check_schema.py
- delete_everly_prosperity_endpoints — archive/backend-diagnostics/delete_everly_prosperity_endpoints.py
- run_migration — archive/backend-diagnostics/run_endpoint_migration.py
- run_migration — archive/backend-diagnostics/run_migration.py
- set_dummy_password — archive/backend-diagnostics/set_dummy_password.py
- test_hierarchy_setup — archive/backend-diagnostics/test_hierarchy_auth.py
- test_endpoint — archive/old-tests/test_all_endpoints.py
- main — archive/old-tests/test_all_endpoints.py
- BuildAPIBrowserTester.__init__ — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.log_test — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_build_api_page_loading — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_endpoint_builder_form — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_form_validation — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_sample_endpoint_creation — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_template_selection — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_other_tabs — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.test_javascript_errors — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.run_all_tests — archive/old-tests/test_build_api_browser.py
- BuildAPIBrowserTester.generate_report — archive/old-tests/test_build_api_browser.py
- main — archive/old-tests/test_build_api_browser.py
- BuildAPITester.__init__ — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.log_test — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_swagger_ui_loading — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_openapi_spec — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_build_api_form_elements — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_builder_tabs — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_javascript_functions — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_template_functionality — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_css_styling — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_error_handling — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.test_sample_endpoint_creation — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.run_all_tests — archive/old-tests/test_build_api_functionality.py
- BuildAPITester.generate_report — archive/old-tests/test_build_api_functionality.py
- main — archive/old-tests/test_build_api_functionality.py
- check — zinnia-modern/backend/check_endpoint_categories.py
- check_examone — zinnia-modern/backend/check_examone_api.py
- fix_endpoint_category — zinnia-modern/backend/fix_endpoint_category.py
- fix_orphaned_apis — zinnia-modern/backend/fix_orphaned_apis.py
- _sanitize_schema_component_name — zinnia-modern/backend/main.py

## Dependency sample
- archive/backend-diagnostics/check_admin_roles.py → app.database, app.models.user
- archive/backend-diagnostics/check_everly_endpoints.py → app.database, app.models.api, app.models.organization, uuid
- archive/backend-diagnostics/check_project_endpoints.py → app.database, app.models.api, app.models.organization, uuid
- archive/backend-diagnostics/check_schema.py → json, sys, re, main
- archive/backend-diagnostics/delete_everly_prosperity_endpoints.py → sys, os, app.database, app.models.api, app.models.organization
- archive/backend-diagnostics/diagnose.py → sys, pathlib, os, dotenv, socket
- archive/backend-diagnostics/run_endpoint_migration.py → os, sys, sqlalchemy, dotenv
- archive/backend-diagnostics/run_migration.py → os, sys, sqlalchemy, dotenv
- archive/backend-diagnostics/set_dummy_password.py → sys, pathlib, sqlalchemy.orm, sqlalchemy, app.database, app.core.security
- archive/backend-diagnostics/test_hierarchy_auth.py → requests, json, sys
- archive/old-tests/test_all_endpoints.py → requests, json, sys, datetime
- archive/old-tests/test_build_api_browser.py → time, json, sys, playwright.sync_api
- archive/old-tests/test_build_api_functionality.py → requests, json, time, sys, urllib.parse
- zinnia-modern/backend/check_all_docs.py → app.database, app.models.api
- zinnia-modern/backend/check_endpoint_categories.py → app.database, app.models.api, uuid
- zinnia-modern/backend/check_examone_api.py → app.database, app.models.api, uuid
- zinnia-modern/backend/check_specific_docs.py → app.database, app.models.api
- zinnia-modern/backend/create_fg_test_data.py → json, uuid, datetime, app.database, app.models.api
- zinnia-modern/backend/diagnose_fg.py → app.database, app.models.api, sqlalchemy
- zinnia-modern/backend/fix_endpoint_category.py → argparse, sys, os, uuid, app.database, app.models.api
- zinnia-modern/backend/fix_orphaned_apis.py → sys, app.database, app.models.api, app.models.organization, sqlalchemy
- zinnia-modern/backend/main.py → typing, fastapi, fastapi.middleware.cors, fastapi.openapi.utils, fastapi.responses, sqlalchemy.orm
- zinnia-modern/backend/alembic/env.py → logging.config, sqlalchemy, alembic, os, sys, app.database
- zinnia-modern/backend/alembic/versions/76f933f8652_add_user_endpoint_access_table.py → alembic, sqlalchemy, sqlalchemy.dialects
- zinnia-modern/backend/alembic/versions/887e04f1d134_add_cloned_from_endpoint_id_and_source_.py → alembic, sqlalchemy

## Documentation graph

## Business context
- [endpoint] GET /api/proxy-download: HTTP surface GET /api/proxy-download
- [endpoint] POST /api/proxy-download/generated-text: HTTP surface POST /api/proxy-download/generated-text
- [endpoint] GET /docs: HTTP surface GET /docs
- [endpoint] GET /openapi-vendor.json: HTTP surface GET /openapi-vendor.json
- [endpoint] GET /openapi-inhouse.json: HTTP surface GET /openapi-inhouse.json
- [endpoint] GET /docs-vendor: HTTP surface GET /docs-vendor
- [endpoint] GET /: HTTP surface GET /
- [endpoint] GET /users: HTTP surface GET /users
- [endpoint] GET /endpoint: HTTP surface GET /endpoint
- [endpoint] GET /resource/{resource_id}: HTTP surface GET /resource/{resource_id}
- [endpoint] POST /admin/deploy: HTTP surface POST /admin/deploy
- [endpoint] GET /admin/deploy/status: HTTP surface GET /admin/deploy/status
- [endpoint] GET /admin/deploy/logs: HTTP surface GET /admin/deploy/logs
- [endpoint] POST /admin/deploy/cancel: HTTP surface POST /admin/deploy/cancel
- [endpoint] POST /admin/deploy/github: HTTP surface POST /admin/deploy/github
- [endpoint] GET /admin/deploy/health: HTTP surface GET /admin/deploy/health
- [endpoint] POST /admin/email-outbox/retry: HTTP surface POST /admin/email-outbox/retry
- [endpoint] GET /admin/email-outbox/health: HTTP surface GET /admin/email-outbox/health
- [endpoint] GET /admin/monitoring/overview: HTTP surface GET /admin/monitoring/overview
- [endpoint] GET /admin/monitoring/health: HTTP surface GET /admin/monitoring/health
- [endpoint] GET /admin/monitoring/api-logs: HTTP surface GET /admin/monitoring/api-logs
- [endpoint] GET /admin/monitoring/user-activity: HTTP surface GET /admin/monitoring/user-activity
- [endpoint] GET /admin/monitoring/errors: HTTP surface GET /admin/monitoring/errors
- [endpoint] GET /admin/monitoring/system-info: HTTP surface GET /admin/monitoring/system-info
- [endpoint] GET /admin/monitoring/ai-usage/overview: HTTP surface GET /admin/monitoring/ai-usage/overview

## File tree (sample)
```
00_INDEX_ZINNIA_AI_AGENT_RESEARCH.md
01_PLATFORM_VISION_STRATEGY.md
02_CORE_ARCHITECTURE.md
02_ZOAS_ZAF_BOT_ANALYSIS.md
03_KNOWLEDGE_GRAPH_RAG.md
03_PART1_DESIGN.md
04_PART2_DESIGN.md
04_SECURITY_ARCHITECTURE.md
05_FINAL_PLAN.md
05_LLM_PROMPT_ARCHITECTURE.md
06_IMPLEMENTATION_ROADMAP.md
AGENT_DESIGN_SUMMARY.md
AGENT_SESSION_SUMMARY.md
AI_AGENTIC_FRAMEWORK_COMPLETE_ARCHITECTURE.md
APPLICATION_STATUS.md
APPROVAL_MEETING_SLIDES.md
AWS_DEPLOYMENT_COMMANDS.md
CATCHY_SME_AGENTIC_NAMES.md
CLEANUP_COMPLETE.md
COMMIT_AND_DEPLOY_QUICK_REFERENCE.md
COMPLETE_RESTART_GUIDE.md
CONTRIBUTING.md
DEPLOYMENT_ANALYSIS.md
DEPLOYMENT_EXECUTIVE_SUMMARY.md
DEPLOY_BUTTON_IMPLEMENTATION_GUIDE.md
DESIGN_REVIEW_CHECKLIST.md
DESKTOP_AI_AGENT_DESIGN.md
DEVELOP_BRANCH_STATUS.md
DISTRIBUTED_BOT_ARCHITECTURE.md
ENTERPRISE_PLATFORM_ROADMAP.md
ENTERPRISE_SECURITY_ARCHITECTURE.md
EXECUTIVE_BRIEF_FINAL_PLAN.md
FEATURE_GUIDE_CLONE_FIXES_SUMMARY.md
FINAL_IMPLEMENTATION_PLAN_COMPREHENSIVE.md
FINAL_SYNC_STATUS.md
GITHUB_SETUP_INSTRUCTIONS.md
GIT_COMMIT_STATUS_REPORT.md
IMPLEMENTATION_ROADMAP.md
INDEX_FINAL_IMPLEMENTATION_PLAN.md
KNOWLEDGE_GRAPH_RAG_ARCHITECTURE.md
PERFECT_20_20_WITHOUT_Z.md
QUICK_START_CHEAT_SHEET.md
README.md
README_AGENT_DESIGN.md
REFRESH_CURSOR_IDE.md
REPO_ANALYSIS_01_RUFLO.md
REPO_ANALYSIS_02_PROMPT_MASTER.md
REPO_ANALYSIS_03_JARVIS.md
REPO_ANALYSIS_04_HEADROOM.md
REPO_ANALYSIS_05_VOXCPM.md
REPO_ANALYSIS_06_COLLAB_PUBLIC.md
REPO_ANALYSIS_07_GRAPHIFY.md
REPO_ANALYSIS_08_PONYTAIL.md
RESTART_SERVICES_GUIDE.md
REVIEW_CHECKLIST.md
TESTING_PLAN_FEATURE_GUIDE_RBAC.md
TEST_RESULTS_FEATURE_GUIDE_RBAC.md
UNIQUE_ORIGINAL_AI_AGENT_NAMES.md
VERIFICATION_REPORT_RBAC_MERGE.md
ZARVIS_AGENT_PLATFORM_DESIGN.md
ZCRAFT_ZFORGER_AGENTIC_OPTIONS.md
ZENITH_PRODUCT_OPTIONS_EXPANDED.md
ZINNIA_AI_AGENT_FINAL_IMPLEMENTATION_PLAN.md
ZINNIA_AI_AGENT_FINAL_PLAN.md
ZINNIA_AI_AGENT_IMPLEMENTATION_PLAN.md
ZOAS_BOT_RAG_ENHANCEMENT_PLAN.md
ZOAS_SME_AGENT_PLATFORM_OPTIONS.md
ZPERFECT_20_20_ALL_OPTIONS.md
__dir__archive
__dir__cloudformation
__dir__database-exports
__dir__docs
__dir__zinnia-modern
__vault__
__wikilink__...
archive/CLEANUP_SUMMARY.md
archive/backend-diagnostics/check_admin_roles.py
archive/backend-diagnostics/check_everly_endpoints.py
archive/backend-diagnostics/check_project_endpoints.py
archive/backend-diagnostics/check_schema.py
```

## Mentrix instructions
1. Respect existing APIs, modules, and dependency edges above
2. Prefer minimal diffs; do not invent endpoints not listed unless required
3. Use Lattice path/neighbors for impact analysis before large refactors
4. Mentrix Ultra Review + gates must pass before Approve → Create PR