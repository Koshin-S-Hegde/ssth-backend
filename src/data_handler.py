import secrets
import bcrypt
import mariadb
from pydantic import BaseModel


class TeamMemberDetails(BaseModel):
    name: str
    email: str
    phone_number: str
    grade: str
    school_name: str
    city: str
    pin_code: str
    team_id: str


class Team(BaseModel):
    id: str
    name: str



class GeneralError(Exception):
    pass

class UserMailExists(Exception):
    pass

class InvalidEmail(Exception):
    pass


class TeamFull(Exception):
    pass

class InvalidTeamId(Exception):
    pass

class NoSuchTeamMember(Exception):
    pass


class DataHandler:
    __connection: mariadb.Connection

    def __init__(self) -> None:
        self.__connection: mariadb.Connection = mariadb.connect(
            user="kosh",
            password="",
            host="localhost",
            port=3306,
            database="ssth",
        )

    def __generate_id(self) -> str:
        return str(secrets.randbelow(1_000_000 - 100_000) + 100_000)

    def __hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()

    def register_user(self, email: str, password: str) -> str:
        user_id = self.__generate_id()
        password = self.__hash_password(password)
        
        try:
            with self.__connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (id, email, password) VALUES (?, ?, ?)",
                    (user_id, email, password)
                )
        except mariadb.IntegrityError as e:
            print(e)
            raise UserMailExists()
        self.__connection.commit()
        return str(user_id)

    def verify_password(self, email: str, password: str) -> bool:
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute("SELECT password FROM users WHERE email = ?", (email, ))
            hashed_password = cursor.fetchall()
            if not hashed_password:
                raise InvalidEmail("Mail doesn't exist")
            hashed_password = hashed_password[0][0].encode("utf-8")
            return bcrypt.checkpw(password.encode("utf-8"), hashed_password)

    def get_user_id(self, email: str) -> str:
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,),
            )
            id = cursor.fetchall()
            if not id:
                raise InvalidEmail("Mail doesn't exist")
            return id[0][0]

    def create_team(self, user_id: str, name: str) -> str:
        team_id = str(self.__generate_id())
        try:
            with self.__connection.cursor() as cursor:
                cursor.execute(
            "INSERT INTO teams (id, user_id, name) VALUES (?, ?, ?)",
            (team_id, user_id, name)
                )
        except mariadb.IntegrityError as e:
            print(e)
            raise UserMailExists(str(e))
        self.__connection.commit()
        return team_id
    
    def get_user_id_for_team(self, team_id: str) -> str:
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute(
                    "SELECT user_id FROM teams WHERE id = ?",
                    (team_id,)
            )
            user_id = cursor.fetchall()
            if not user_id:
                raise InvalidTeamId
        return str(user_id[0][0])

    def add_team_member(
            self,
            team_id: str,
            name: str,
            email: str,
            phone_number: str,
            grade: int,
            school_name: str,
            city: str,
            pin_code: str,
    ) -> str:
        member_id = self.__generate_id()
        
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM teams WHERE id = ?", (team_id,))
            response = cursor.fetchall()
            if len(response) == 0:
                raise InvalidTeamId()
            cursor.execute(
                "SELECT 1 FROM team_members WHERE team_id = ?", (team_id,)
            )
            response = len(cursor.fetchall())
            if response >= 4:
                raise TeamFull()
            cursor.execute(
                """INSERT INTO team_members 
               (id, team_id, name, email, phone_number, grade, school_name, city, pin_code) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (member_id, team_id, name, email, phone_number, grade, school_name, city, pin_code)
            )
        self.__connection.commit()
        return member_id

    def get_user_teams(self, user_id: str) -> list[Team]:
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute(
                    "SELECT id, name FROM teams WHERE user_id = ?",
                    (user_id,)
            )
            return [
                    Team(id=str(i[0]), name=i[1])
                    for i in cursor.fetchall()
            ]

    def get_team_members(self, team_id: str) -> list[str]:
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute(
                    """SELECT id FROM team_members WHERE team_id = ?""",
                    (team_id,),
            )
            return [str(i[0]) for i in cursor.fetchall()]
        
    def get_team_member_details(self, team_id: str, team_member_id: str) -> TeamMemberDetails:
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute(
                    """SELECT name, email, phone_number, grade, school_name, city, pin_code, team_id FROM team_members WHERE id = ? AND team_id = ?""",
                    (team_member_id, team_id,),
            )
            response = cursor.fetchall()
            if not response:
                raise NoSuchTeamMember()
            response = response[0]
            return TeamMemberDetails(
                    name=response[0],
                    email=response[1],
                    phone_number=str(response[2]),
                    grade=str(response[3]),
                    school_name=response[4],
                    city=response[5],
                    pin_code=str(response[6]),
                    team_id=str(response[7]),
            )

    def add_document(self, team_id: str, path: str) -> str:
        doc_id = self.__generate_id()
        
        cursor: mariadb.Cursor
        with self.__connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO TeamDocument (id, team_id, path) VALUES (?, ?, ?)",
                (doc_id, team_id, path)
            )
        return doc_id


    #def get_team_documents(self, team_id: int) -> List[TeamDocument]:
    #    """Get all documents for a team"""
    #    results = self._execute_query(
    #        "SELECT id, team_id, path FROM TeamDocument WHERE team_id = ?",
    #        (team_id,),
    #        fetch_all=True
    #    )
    #    return [TeamDocument(row[0], row[1], row[2]) for row in results] if results else []
