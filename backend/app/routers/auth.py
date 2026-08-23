# Import FastAPI components:
# APIRouter -> Used to group related API endpoints
# Depends -> Used for dependency injection
# HTTPException -> Used to return HTTP error responses
# status -> Provides standard HTTP status codes
from fastapi import APIRouter, Depends, HTTPException, status

# Import SQLAlchemy Session for database operations
from sqlalchemy.orm import Session

# Import the database dependency that provides a database session
from backend.app.database import get_db

# Import the User database model
from backend.app.models import User

# Import Pydantic schemas used for request validation
# and response formatting
from backend.app.schemas import (
    UserCreate,
    UserLogin,
    UserOut,
    Token
)

# Import authentication utility functions
from backend.app.auth.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)


# Create a router for all authentication-related endpoints.
#
# All routes in this file will start with "/auth".
# For example:
# POST /auth/register
# POST /auth/login
# GET  /auth/me
#
# The tag is used to group these endpoints under
# "Authentication" in the FastAPI Swagger documentation.
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# -------------------------------------------------------------------
# REGISTER ENDPOINT
# -------------------------------------------------------------------

# Create a new user account.
#
# Request:
# POST /auth/register
#
# The incoming request body must follow the UserCreate schema.
#
# response_model=UserOut ensures that the response follows
# the UserOut schema and does not expose sensitive fields
# such as the hashed password.
#
# status_code=201 indicates that a new resource was created.
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.

    Steps:
    1. Check whether the email already exists.
    2. Hash the user's password.
    3. Create a new User object.
    4. Save the user to the database.
    5. Return the newly created user.
    """

    # Check whether a user with the same email
    # already exists in the database.
    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    # If the email is already registered,
    # return a 400 Bad Request error.
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Hash the plain-text password before storing it.
    #
    # The original password is never stored directly
    # in the database.
    hashed_pwd = get_password_hash(user_data.password)

    # Create a new User database object.
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_pwd,
        role=user_data.role,
        full_name=user_data.full_name,

        # merchant_name is only stored if the user's
        # role is "merchant".
        merchant_name=(
            user_data.merchant_name
            if user_data.role == "merchant"
            else None
        )
    )

    # Add the new user object to the current database session.
    db.add(new_user)

    # Commit the transaction to permanently save
    # the new user in the database.
    db.commit()

    # Refresh the object to retrieve updated database values,
    # such as automatically generated fields like user ID.
    db.refresh(new_user)

    # Return the newly created user.
    #
    # FastAPI converts it into the UserOut response schema.
    return new_user


# -------------------------------------------------------------------
# LOGIN ENDPOINT
# -------------------------------------------------------------------

# Authenticate a user and generate a JWT access token.
#
# Request:
# POST /auth/login
#
# The request body must follow the UserLogin schema.
#
# The response follows the Token schema.
@router.post(
    "/login",
    response_model=Token
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticate a user and generate an access token.

    Steps:
    1. Find the user using the provided email.
    2. Verify the entered password against the stored hashed password.
    3. If authentication fails, return a 401 error.
    4. If successful, create a JWT access token.
    5. Return the access token to the client.
    """

    # Search the database for a user with the given email.
    user = (
        db.query(User)
        .filter(User.email == login_data.email)
        .first()
    )

    # Check two conditions:
    #
    # 1. The user exists.
    # 2. The provided password matches the stored hashed password.
    #
    # If either condition fails, authentication is rejected.
    if (
        not user
        or not verify_password(
            login_data.password,
            user.hashed_password
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    # Create a JWT access token containing useful user information.
    #
    # The token payload includes:
    # - email: User's email address
    # - role: User's role
    # - user_id: Unique database ID of the user
    access_token = create_access_token(
        data={
            "email": user.email,
            "role": user.role,
            "user_id": user.id
        }
    )

    # Return the JWT token.
    #
    # The client will typically send this token in future requests
    # using the Authorization header:
    #
    # Authorization: Bearer <access_token>
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# -------------------------------------------------------------------
# CURRENT USER ENDPOINT
# -------------------------------------------------------------------

# Return information about the currently authenticated user.
#
# Request:
# GET /auth/me
#
# This endpoint requires a valid JWT access token.
@router.get(
    "/me",
    response_model=UserOut
)
def get_me(
    # FastAPI calls get_current_user before executing this function.
    #
    # The function extracts and validates the JWT token,
    # identifies the user, and returns the corresponding
    # User object.
    current_user: User = Depends(get_current_user)
):
    """
    Return the currently authenticated user's information.

    The user is identified using the JWT token provided
    in the Authorization header.
    """

    # Return the authenticated user's information.
    #
    # The response_model ensures that only fields defined
    # in UserOut are returned to the client.
    return current_user