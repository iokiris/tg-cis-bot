# MARKDOWN !!!

import db
import utils
from config import CHAT_LINK, CHANNEL_LINK
from utils import translated


def get_subscribed_text(uid: int) -> str:
    user = db.get_user_info(uid)
    return translated('participation_text', uid).format(
        wallet=user[6],
        number=user[0]
    )


def get_ref_message(uid: int) -> str:
    user_info = db.get_user_info(uid)
    referral_link = utils.generate_referral_link(uid)
    users_count = db.Data.users_count

    return f"""
<b>{translated('referral_link', uid)}</b>\n
<a href="{referral_link}">{referral_link}</a>\n\n
<b>{translated('referral_statistics', uid)}</b>\n
{translated('referrals_count', uid)}: {user_info[2]}\n
{translated('participants_count', uid)}: {users_count}
"""

