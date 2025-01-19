import psycopg2

import tables
from config import DatabaseConfig

connection = psycopg2.connect(**DatabaseConfig.as_dict())
cursor = connection.cursor()


class Data:
    q = cursor.execute("SELECT COUNT(*) FROM users_info")
    users_count = cursor.fetchone()[0]


# users_info
# id, stage, ref_counter, reffered_by, name, tg_id


def register_user(id: int, name: str, reffered_by: int, wallet: str, lang_code: str):
    if not get_user_stage(id):
        sql = "INSERT INTO users_info (stage, ref_counter, referred_by, name, tg_id, wallet, lang) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(sql, ('real_user', 1, reffered_by, name, id, wallet, lang_code))
        connection.commit()
        if reffered_by:
            sql = "UPDATE users_info SET ref_counter = ref_counter + 1 WHERE tg_id = %s"
            cursor.execute(sql, (reffered_by,))
            connection.commit()
    Data.users_count += 1

def get_top_100():
    sql = "SELECT id, name, ref_counter FROM users_info ORDER BY ref_counter DESC LIMIT 100"
    cursor.execute(sql)
    return cursor.fetchall()

def get_all_users():
    sql = "SELECT id, name, ref_counter FROM users_info;"
    cursor.execute(sql)
    return cursor.fetchall()

def get_user_pos(id: int):
    sql = "SELECT id FROM users_info WHERE tg_id = %s"
    cursor.execute(sql, (id,))
    return cursor.fetchone()[0]


def get_user_info(tg_id: int):
    sql = "SELECT * FROM users_info WHERE tg_id = %s;"
    cursor.execute(sql, (tg_id,))
    return cursor.fetchone()


def get_user_counter(tg_id: int):
    sql = "SELECT ref_counter FROM users_info WHERE tg_id = %s;"
    cursor.execute(sql, (tg_id,))
    try:
        return cursor.fetchone()[0]
    except TypeError:
        return 0


def get_user_stage(tg_id: int):
    sql = "SELECT stage FROM users_info WHERE tg_id = %s;"
    cursor.execute(sql, (tg_id,))
    try:
        return cursor.fetchone()[0]
    except TypeError:
        return None


def set_user_stage(tg_id: int, stage: str):
    sql = "UPDATE users_info SET stage = %s WHERE tg_id = %s;"
    cursor.execute(sql, (stage, tg_id))


def get_user_position_and_surroundings(user_id):
    cursor.execute("""
        WITH ranked_users AS (
            SELECT tg_id, name, ref_counter, ROW_NUMBER() OVER (ORDER BY ref_counter DESC) AS position
            FROM users_info
        ),
        user_position AS (
            SELECT position FROM ranked_users WHERE tg_id = %s
        )
        SELECT tg_id, name, ref_counter, position
        FROM ranked_users
        WHERE position <= 5
        OR position = (SELECT position FROM user_position) - 2
        OR position = (SELECT position FROM user_position) - 1
        OR position = (SELECT position FROM user_position)
        OR position = (SELECT position FROM user_position) + 1
        OR position = (SELECT position FROM user_position) + 2
        ORDER BY position
    """, (user_id,))
    users = cursor.fetchall()
    user_position = next((user[3] for user in users if user[0] == user_id), None)
    surrounding_users = [{"id": user[0], "name": user[1], "ref_counter": user[2], "position": user[3]} for user in users]

    return user_position, surrounding_users

def get_user_language(tg_id: int):
    sql = "SELECT lang FROM users_info WHERE tg_id = %s;"
    cursor.execute(sql, (tg_id,))
    return cursor.fetchone()[0]

