from langgraph_sdk import Auth

# See https://docs.langchain.com/langsmith/auth
auth = Auth()

# Authenticate
@auth.authenticate
async def get_current_user(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Validate JWT tokens and extract user information."""
    print( f"authorization{authorization}", flush=True )
    assert authorization
    scheme, token = authorization.split()
    print( f"scheme={scheme} token={token}", flush=True )

    # Validate with your auth provider
    if scheme!="User":
        raise Auth.exceptions.HTTPException(
            status_code=401,
            detail="Access Denied"
        )
    return {
        "identity": token,
        "email": "spam@oracle.com",
        "is_authenticated": True
    }
    
# Access only your own threads    
# @auth.on
# async def owner_only(ctx: Auth.types.AuthContext, value: dict):
#     metadata = value.setdefault("metadata", {})
#     metadata["owner"] = ctx.user.identity
#     return {"owner": ctx.user.identity}