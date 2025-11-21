import hashlib

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import insert, select, update, delete, desc

from db.models import (
    CPayments,
    ManualPaymentLink,
    ManualPayments,
    UserLink,
    VPNUsers,
    YPayments,
)
import glv

engine = create_async_engine(glv.config['DB_URL'])

async def create_vpn_profile(tg_id: int):
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result: VPNUsers = (await conn.execute(sql_query)).fetchone()
        if result is not None:
            return
        vpn_hash = hashlib.md5(str(tg_id).encode()).hexdigest()
        sql_query = insert(VPNUsers).values(tg_id=tg_id, vpn_id=vpn_hash)
        await conn.execute(sql_query)
        await conn.commit()

async def get_marzban_profile_db(tg_id: int) -> VPNUsers:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        profile: VPNUsers | None = result.scalars().first()
    return profile

async def get_marzban_profile_by_vpn_id(vpn_id: str):
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.vpn_id == vpn_id)
        result = await conn.execute(sql_query)
        profile: VPNUsers | None = result.scalars().first()
    return profile


async def get_primary_user_link(tg_id: int) -> UserLink | None:
    links = await get_links_by_tg_id(tg_id)
    return links[0] if links else None


async def get_links_by_tg_id(tg_id: int) -> list[UserLink]:
    async with engine.connect() as conn:
        sql_q = select(UserLink).where(UserLink.tg_id == tg_id)
        result = await conn.execute(sql_q)
        rows = result.fetchall()

    links: list[UserLink] = []
    for row in rows:
        link = row[0] if isinstance(row, tuple) else row
        if isinstance(link, UserLink):
            links.append(link)
    return links


async def get_link_by_marzban_user(username: str) -> UserLink | None:
    async with engine.connect() as conn:
        sql_q = select(UserLink).where(UserLink.marzban_user == username)
        result = await conn.execute(sql_q)
        row = result.first()

    if row is None:
        return None

    link = row[0] if isinstance(row, tuple) else row
    return link if isinstance(link, UserLink) else None


async def add_user_link(tg_id: int, tg_username: str | None, marzban_user: str):
    async with engine.connect() as conn:
        sql_q = insert(UserLink).values(
            tg_id=tg_id,
            tg_username=tg_username,
            marzban_user=marzban_user,
        )
        await conn.execute(sql_q)
        await conn.commit()


async def update_user_link_username(tg_id: int, tg_username: str | None):
    async with engine.connect() as conn:
        sql_q = (
            update(UserLink)
            .where(UserLink.tg_id == tg_id)
            .values(tg_username=tg_username)
        )
        await conn.execute(sql_q)
        await conn.commit()


async def delete_user_link(marzban_username: str):
    async with engine.connect() as conn:
        sql_q = delete(UserLink).where(UserLink.marzban_user == marzban_username)
        await conn.execute(sql_q)
        await conn.commit()


async def get_all_linked_usernames() -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(select(UserLink.marzban_user))
        usernames = set(result.scalars().all())
    return usernames

async def had_test_sub(tg_id: int) -> bool:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        profile: VPNUsers | None = result.scalars().first()
    return bool(profile and profile.test)

async def update_test_subscription_state(tg_id):
    async with engine.connect() as conn:
        sql_q = update(VPNUsers).where(VPNUsers.tg_id == tg_id).values(test=True)
        await conn.execute(sql_q)
        await conn.commit()

async def add_yookassa_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, payment_id) -> dict:
    async with engine.connect() as conn:
        sql_q = insert(YPayments).values(tg_id=tg_id, payment_id=payment_id, chat_id=chat_id, callback=callback, lang=lang_code)
        result = await conn.execute(sql_q)
        await conn.commit()
        return result.inserted_primary_key[0]

async def add_cryptomus_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, data) -> dict:
    async with engine.connect() as conn:
        sql_q = insert(CPayments).values(tg_id=tg_id, payment_uuid=data['order_id'], order_id=data['order_id'], chat_id=chat_id, callback=callback, lang=lang_code)
        result = await conn.execute(sql_q)
        await conn.commit()
        return result.inserted_primary_key[0]

async def get_yookassa_payment(payment_id) -> YPayments:
    async with engine.connect() as conn:
        sql_q = select(YPayments).where(YPayments.payment_id == payment_id)
        result = await conn.execute(sql_q)
        payment: YPayments | None = result.scalars().first()
    return payment

async def get_cryptomus_payment(order_id) -> CPayments:
    async with engine.connect() as conn:
        sql_q = select(CPayments).where(CPayments.order_id == order_id)
        result = await conn.execute(sql_q)
        payment: CPayments | None = result.scalars().first()
    return payment

async def delete_payment(payment_id):
    async with engine.connect() as conn:
        sql_q = delete(YPayments).where(YPayments.payment_id == payment_id)
        await conn.execute(sql_q)
        await conn.commit()
        sql_q = delete(CPayments).where(CPayments.payment_uuid == payment_id)
        await conn.execute(sql_q)
        await conn.commit()


async def add_manual_payment(
    tg_id: int,
    callback: str,
    chat_id: int,
    lang_code: str,
    username: str | None = None,
    status: str = "manual_pending",
    plan_name: str | None = None,
    amount: str | None = None,
) -> int:
    async with engine.connect() as conn:
        sql_q = insert(ManualPayments).values(
            tg_id=tg_id,
            username=username,
            callback=callback,
            chat_id=chat_id,
            lang=lang_code,
            status=status,
            plan_name=plan_name,
            amount=amount,
        )
        result = await conn.execute(sql_q)
        await conn.commit()
        return result.inserted_primary_key[0]


async def get_manual_payment(payment_id) -> ManualPayments:
    async with engine.connect() as conn:
        sql_q = select(ManualPayments).where(ManualPayments.id == payment_id)
        result = await conn.execute(sql_q)
        payment: ManualPayments | None = result.scalars().first()
    return payment


async def add_manual_payment_link(payment_id: int, marzban_user: str) -> None:
    async with engine.connect() as conn:
        sql_q = insert(ManualPaymentLink).values(payment_id=payment_id, marzban_user=marzban_user)
        await conn.execute(sql_q)
        await conn.commit()


async def get_manual_payment_links(payment_id: int) -> list[str]:
    async with engine.connect() as conn:
        sql_q = select(ManualPaymentLink.marzban_user).where(ManualPaymentLink.payment_id == payment_id)
        result = await conn.execute(sql_q)
        usernames = list(result.scalars().all())
    return usernames


async def update_manual_payment(payment_id, **kwargs):
    async with engine.connect() as conn:
        sql_q = update(ManualPayments).where(ManualPayments.id == payment_id).values(**kwargs)
        await conn.execute(sql_q)
        await conn.commit()


async def get_latest_manual_payment_by_status(tg_id: int, statuses: list[str]) -> ManualPayments | None:
    async with engine.connect() as conn:
        sql_q = (
            select(ManualPayments)
            .where(ManualPayments.tg_id == tg_id, ManualPayments.status.in_(statuses))
            .order_by(desc(ManualPayments.id))
        )
        result = await conn.execute(sql_q)
        payment: ManualPayments | None = result.scalars().first()
    return payment
