import hashlib

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import insert, select, update, delete, desc

from db.models import YPayments, CPayments, VPNUsers, ManualPayments
import glv

engine = create_async_engine(glv.config['DB_URL'])

async def create_vpn_profile(tg_id: int):
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        existing: VPNUsers | None = result.scalar_one_or_none()
        if existing is not None:
            return
        hash = hashlib.md5(str(tg_id).encode()).hexdigest()
        sql_query = insert(VPNUsers).values(tg_id=tg_id, vpn_id=hash)
        await conn.execute(sql_query)
        await conn.commit()

async def get_marzban_profile_db(tg_id: int) -> VPNUsers | None:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        return result.scalar_one_or_none()

async def get_marzban_profile_by_vpn_id(vpn_id: str):
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.vpn_id == vpn_id)
        result = await conn.execute(sql_query)
        return result.scalar_one_or_none()

async def had_test_sub(tg_id: int) -> bool:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        user: VPNUsers | None = result.scalar_one_or_none()
    return bool(user.test) if user is not None else False

async def update_test_subscription_state(tg_id):
    async with engine.connect() as conn:
        sql_q = update(VPNUsers).where(VPNUsers.tg_id == tg_id).values(test=True)
        await conn.execute(sql_q)
        await conn.commit()

async def add_yookassa_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, payment_id) -> dict:
    async with engine.connect() as conn:
        sql_q = insert(YPayments).values(tg_id=tg_id, payment_id=payment_id, chat_id=chat_id, callback=callback, lang=lang_code)
        await conn.execute(sql_q)
        await conn.commit()

async def add_cryptomus_payment(tg_id: int, callback: str, chat_id: int, lang_code: str, data) -> dict:
    async with engine.connect() as conn:
        sql_q = insert(CPayments).values(tg_id=tg_id, payment_uuid=data['order_id'], order_id=data['order_id'], chat_id=chat_id, callback=callback, lang=lang_code)
        await conn.execute(sql_q)
        await conn.commit()

async def get_yookassa_payment(payment_id) -> YPayments:
    async with engine.connect() as conn:
        sql_q = select(YPayments).where(YPayments.payment_id == payment_id)
        payment: YPayments = (await conn.execute(sql_q)).fetchone()
    return payment

async def get_cryptomus_payment(order_id) -> CPayments:
    async with engine.connect() as conn:
        sql_q = select(CPayments).where(CPayments.order_id == order_id)
        payment: CPayments = (await conn.execute(sql_q)).fetchone()
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
        payment: ManualPayments = (await conn.execute(sql_q)).fetchone()
    return payment


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
        payment: ManualPayments = (await conn.execute(sql_q)).fetchone()
    return payment
