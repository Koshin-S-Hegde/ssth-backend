from typing import Annotated
from fastapi import Cookie, FastAPI, File, Response
from pydantic import BaseModel
import bcrypt
from data_handler import DataHandler, InvalidEmail, InvalidTeamId, NoSuchTeamMember, Team, TeamFull, TeamMemberDetails, UserMailExists


app: FastAPI = FastAPI()
KEY = b"8u8dm82e9e"
data_handler = DataHandler()


class CookiesBase(BaseModel):
    user_id: str
    hashed_user_id: str
Cookies = Annotated[CookiesBase, Cookie()]
RequestFile = Annotated[bytes, File()]


class GetIdResponse(BaseModel):
    id: str
    success: bool

class AuthenticationFailure(Exception):
    pass


def get_id(cookies: Cookies) -> str:
    hashed_user_id = cookies.hashed_user_id.encode("utf-8")
    user_id = cookies.user_id.encode("utf-8")
    try:
        correct = bcrypt.checkpw(user_id, hashed_user_id)
    except ValueError:
        raise AuthenticationFailure()
    if not correct:
        raise AuthenticationFailure()
    return user_id.decode("utf-8")


@app.post("/api/get-id")
async def get_current_id(cookie: Cookies) -> GetIdResponse:
    hashed_user_id = cookie.hashed_user_id.encode("utf-8")
    user_id = cookie.user_id.encode("utf-8")
    correct = bcrypt.checkpw(user_id, hashed_user_id)
    if not correct:
        return GetIdResponse(id="-1", success=False)
    return GetIdResponse(id=user_id.decode("utf-8"), success=True)


class RegisterRequest(BaseModel):
    email: str
    password: str

class RegisterResponse(BaseModel):
    id: str
    success: bool
    email_unique: bool
    password_acceptable: bool

@app.post("/api/register")
async def register(request: RegisterRequest, response: Response) -> RegisterResponse:
    if len(request.password) < 8:
        return RegisterResponse(
                id="-1",
                success=False,
                email_unique=True,
                password_acceptable=False,
        )
    try:
        id = data_handler.register_user(email=request.email, password=request.password)
        response.set_cookie("user_id", id)
        response.set_cookie(
                "hashed_user_id",
                bcrypt.hashpw(id.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        )
        return RegisterResponse(
                id=id,
                success=True,
                email_unique=True,
                password_acceptable=True,
        )
    except UserMailExists:
        return RegisterResponse(
                id="-1",
                success=False,
                email_unique=False,
                password_acceptable=True,
        )


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    email_correct: bool
    password_correct: bool


@app.post("/api/login")
async def login(request: LoginRequest, response: Response) -> LoginResponse:
    try:
        password_correct = data_handler.verify_password(request.email, request.password)
        if not password_correct:
            return LoginResponse(
                    success=False,
                    email_correct=True,
                    password_correct=False
            )
        id = data_handler.get_user_id(request.email)
        response.set_cookie("user_id", str(id))
        response.set_cookie(
                "hashed_user_id",
                bcrypt.hashpw(str(id).encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        )
        return LoginResponse(
                success=True,
                email_correct=True,
                password_correct=True
        )
    except InvalidEmail:
        return LoginResponse(
                success=False,
                email_correct=False,
                password_correct=True
        )


@app.post("/api/logout")
async def logout(response: Response) -> None:
    response.delete_cookie("user_id")
    response.delete_cookie("hashed_user_id")


class CreateTeamRequest(BaseModel):
    team_name: str


class CreateTeamResponse(BaseModel):
    team_id: str|int
    success: bool
    logged_in: bool


@app.post("/api/create-team")
async def create_team(cookies: Cookies, request: CreateTeamRequest) -> CreateTeamResponse:
    try:
        user_id = get_id(cookies)
    except AuthenticationFailure:
        return CreateTeamResponse(team_id=-1, success=False, logged_in=False)
    id = data_handler.create_team(user_id=user_id, name=request.team_name)
    return CreateTeamResponse(team_id=id,success=True, logged_in=True)


class AddTeamMemberRequest(BaseModel):
    team_id: str
    name: str
    email: str
    phone_number: str
    grade: str
    school_name: str
    city: str
    pin_code: str


class AddTeamMemberResponse(BaseModel):
    success: bool
    logged_in: bool
    space_available: bool
    team_created: bool
    user_team_match: bool


@app.post("/api/add-team-member")
async def add_team_member(cookies: Cookies, request: AddTeamMemberRequest) -> AddTeamMemberResponse:
    try:
        user_id = get_id(cookies)
    except AuthenticationFailure:
        return AddTeamMemberResponse(success=False, logged_in=False, space_available=True, team_created=True, user_team_match=True)
    try:
        assert user_id == data_handler.get_user_id_for_team(request.team_id)
    except InvalidTeamId:
        return AddTeamMemberResponse(
                success=False,
                logged_in=True,
                space_available=True,
                team_created=False,
                user_team_match=False,
        )
    except AssertionError:
        return AddTeamMemberResponse(
                success=False,
                logged_in=True,
                space_available=True,
                team_created=True,
                user_team_match=False,
        )
    try:
        data_handler.add_team_member(
                team_id=request.team_id,
                name=request.name,
                email=request.email,
                phone_number=request.phone_number,
                grade=request.grade,
                school_name=request.school_name,
                city=request.city,
                pin_code=request.pin_code
        )
        return AddTeamMemberResponse(
                success=True,
                logged_in=True,
                space_available=True,
                team_created=True,
                user_team_match=True,
        )
    except TeamFull:
        return AddTeamMemberResponse(
                success=False,
                logged_in=True,
                space_available=False,
                team_created=True,
                user_team_match=True,
        )
    except InvalidTeamId:
        return AddTeamMemberResponse(
                success=False,
                logged_in=True,
                space_available=False,
                team_created=False,
                user_team_match=True,
        )


class GetTeamsResponse(BaseModel):
    team_ids: list[Team]
    success: bool
    logged_in: bool

@app.post("/api/get-teams")
async def get_teams(cookies: Cookies) -> GetTeamsResponse:
    try:
        user_id = get_id(cookies)
    except AuthenticationFailure:
        return GetTeamsResponse(team_ids=[], success=False, logged_in=False)
    return GetTeamsResponse(
            team_ids=data_handler.get_user_teams(user_id),
            success=True,
            logged_in=True,
    )


class GetTeamMemberRequest(BaseModel):
    team_id: str

class GetTeamMemberResoponse(BaseModel):
    team_member_ids: list[str]
    success: bool
    logged_in: bool
    user_team_match: bool

@app.post("/api/get-team-members")
async def get_team_members(cookies: Cookies, request: GetTeamMemberRequest) -> GetTeamMemberResoponse:
    try:
        assert data_handler.get_user_id_for_team(request.team_id) == get_id(cookies)
    except AuthenticationFailure:
        return GetTeamMemberResoponse(
                team_member_ids=[],
                success=False,
                logged_in=False,
                user_team_match=True,
        )
    except AssertionError:
        return GetTeamMemberResoponse(
                team_member_ids=[],
                success=False,
                logged_in=True,
                user_team_match=False,
        )
    return GetTeamMemberResoponse(
            team_member_ids=data_handler.get_team_members(request.team_id),
            success=True,
            logged_in=True,
            user_team_match=True
    )


class GetTeamMemberDetailsRequest(BaseModel):
    team_id: str
    team_member_id: str

class GetTeamMemberDeatailsResoponse(BaseModel):
    team_member_details: TeamMemberDetails|None
    success: bool
    logged_in: bool
    user_team_match: bool
    team_member_exists: bool

@app.post("/api/get-team-member-details")
async def get_team_member_details(cookies: Cookies, request: GetTeamMemberDetailsRequest) -> GetTeamMemberDeatailsResoponse:
    try:
        assert data_handler.get_user_id_for_team(request.team_id) == get_id(cookies)
    except AuthenticationFailure:
        return GetTeamMemberDeatailsResoponse(
                team_member_details=None,
                success=False,
                logged_in=False,
                user_team_match=True,
                team_member_exists=True,
        )
    except AssertionError:
        return GetTeamMemberDeatailsResoponse(
                team_member_details=None,
                success=False,
                logged_in=True,
                user_team_match=False,
                team_member_exists=True,
        )
    try:
        return GetTeamMemberDeatailsResoponse(
                team_member_details=data_handler.get_team_member_details(request.team_id, request.team_member_id),
                success=True,
                logged_in=True,
                user_team_match=True,
                team_member_exists=True,
        )
    except NoSuchTeamMember:
        return GetTeamMemberDeatailsResoponse(
                team_member_details=None,
                success=False,
                logged_in=True,
                user_team_match=True,
                team_member_exists=False,
        )
