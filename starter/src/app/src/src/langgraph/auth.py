from langgraph_sdk import Auth

auth = Auth()

@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Validate JWT tokens and extract user information."""
    print( f"authorization{authorization}", flush=True )
    assert authorization
    scheme, token = authorization.split()
    assert scheme.lower() == "bearer"
    print( f"scheme{scheme} token{token}", flush=True )

    # Validate with your auth provider
    if not token or token!="public":
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Access Denied"
        )
    return {
        "identity": "public",
        "email": "spam@oracle.com",
        "is_authenticated": True
    }
    
@auth.on
async def owner_only(ctx: Auth.types.AuthContext, value: dict):
    metadata = value.setdefault("metadata", {})
    metadata["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}