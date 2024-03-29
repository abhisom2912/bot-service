from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder

from models import User, UserUpdate

user_router = APIRouter()

# API to register a user and save them in the database
@user_router.post("/", response_description="Sign in a user using Discord", status_code=status.HTTP_201_CREATED)
def create_user(request: Request, user: User = Body(...)):
    user = jsonable_encoder(user)
    if request.app.database["users"].find_one( {"email": user['email']} ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This email already exists")
    new_user = request.app.database["users"].insert_one(user)
    return new_user.inserted_id

# API to get the details of all users from the database
@user_router.get("/", response_description="List all users", response_model=list[User])
def list_users(request: Request):
    users = list(request.app.database["users"].find(limit=100))
    return users

# API to get the details of a single user from the database
@user_router.get("/{id}", response_description="Get a single user by id", response_model=User)
def find_user(id: str, request: Request):
    if (user := request.app.database["users"].find_one({"_id": id})) is not None:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User with ID {id} not found")

# API to update the details of a user in the database
@user_router.put("/{id}", response_description="Update a user details", response_model=User)
def update_user(id: str, request: Request, user: UserUpdate = Body(...)):
    user = {k: v for k, v in user.dict().items() if v is not None}
    if len(user) >= 1:
        update_result = request.app.database["users"].update_one(
            {"_id": id}, {"$set": user}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {id} not found")

    if (
        existing_user := request.app.database["users"].find_one({"_id": id})
    ) is not None:
        return existing_user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {id} not found")

# API to delete the details of a user from the database
@user_router.delete("/{id}", response_description="Delete a user")
def delete_user(id: str, request: Request, response: Response):
    delete_result = request.app.database["users"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"User with ID {id} not found")
