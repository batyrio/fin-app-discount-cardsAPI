import jwt
import psycopg2
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from config import DB_NAME, DB_HOST, DB_PORT, DB_PASS, DB_USER, SECRET_KEY
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


class DiscountCard(BaseModel):
    card_number: str
    card_name: str
    discount: float
    fk_cards_users: int


class InputCode(BaseModel):
    code: str


app = FastAPI()
security = HTTPBearer()


connection = psycopg2.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASS,
    database=DB_NAME,
    port=DB_PORT,
)
connection.autocommit = True


@app.on_event("startup")
async def startup_event():
    print("Сервер запущен")


@app.on_event("shutdown")
async def shutdown_event():
    connection.close()
    print("Сервер остановлен")



async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    try:
        secret_key = SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        user_id = payload.get("id")
        return user_id

    except jwt.DecodeError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expired token",
            headers={"WWW-Authenticate": "Bearer"}, )


    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL:", ex)


@app.post("/cards")
async def add_subscription(card: DiscountCard, user_id: int = Depends(get_current_user_id),):

    try:
        with connection.cursor() as cursor:

            cursor.execute("SELECT * FROM users WHERE id = %s;", (user_id,))
            user_data = cursor.fetchone()

            if user_data:

                cursor.execute(
                    """
                    INSERT INTO cards (card_number, card_name, discount, fk_cards_users)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (card.card_number, card.card_name, card.discount, user_id),
                )

                return {"message": "Дисконтная карта успешно добавлена!."}
            else:
                return {"error": "Пользователь не найден."}

    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL:", ex)


@app.put("/cards/{card_id}")
async def update_card(card_id: int, item: DiscountCard, user_id: int = Depends(get_current_user_id)):
    card_number = item.card_number
    card_name = item.card_name
    discount = item.discount

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM cards WHERE id = %s AND fk_cards_users = %s;",
                (card_id, user_id),
            )
            card_data = cursor.fetchone()

            if card_data:
                cursor.execute(
                    """UPDATE cards SET card_number = %s, card_name = %s, discount = %s,
                    fk_cards_users = %s WHERE id = %s;""",
                    (card_number, card_name, discount, user_id, card_id)
                )
            return {"done": f"Дисконтная карта {card_name} успешно обновлена!"}

    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL:", ex)


@app.get("/cards")
async def get_user_cards(user_id: int = Depends(get_current_user_id)):
    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """SELECT * FROM cards WHERE fk_cards_users = %s;""",
                (user_id,)
            )

            cards = cursor.fetchall()

            if cards:

                cards_list = []

                for card in cards:
                    card_data = {
                        "card_number": card[1],
                        "card_name": card[2],
                        "discount": card[3],
                        }
                    cards_list.append(card_data)

                return {"cards": cards_list}
            else:
                return {"cards": []}

    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL:", ex)


@app.delete("/cards/{card_id}")
async def delete_card(card_id: int, user_id: int = Depends(get_current_user_id)):
    try:
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT * FROM cards WHERE id = %s AND fk_cards_users = %s;",
                (card_id, user_id),
            )
            card_data = cursor.fetchone()

            if card_data:
                cursor.execute(
                    "DELETE FROM cards WHERE id = %s;",
                    (card_id,),
                )

                return {"message": f"Дисконтная карта {card_id} успешно удалена."}
            else:
                return {"error": f"Дисконтная карта {card_id} не найдена или не принадлежит пользователю."}


    except Exception as ex:
        print("[INFO] Ошибка при работе с PostgreSQL:", ex)


