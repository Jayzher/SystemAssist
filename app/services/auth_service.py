# auth_service.py — deprecated.
# SystemAssist v2 uses API key authentication. There are no internal user accounts.
# All user identity is provided as user_id in the request payload by the calling system.
# Authentication is enforced via app/security/rbac.py (verify_api_key dependency).
