import hashlib

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import insert, select, update, delete, desc

from db.models import YPayments, CPayments, VPNUsers, ManualPayments
import glv

engine = create_async_engine(glv.config['DB_URL'])


async def create_vpn_profile(tg_id: int):
    async with engine.connect() as conn:
        # Проверяем, есть ли уже пользователь
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        existing_user: VPNUsers | None = result.scalar_one_or_none()

        if existing_user is not None:
            return

        hash_ = hashlib.md5(str(tg_id).encode()).hexdigest()
        sql_query = insert(VPNUsers).values(tg_id=tg_id, vpn_id=hash_)
        await conn.execute(sql_query)
        await conn.commit()


async def get_marzban_profile_db(tg_id: int) -> VPNUsers | None:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        user: VPNUsers | None = result.scalar_one_or_none()
    return user


async def get_marzban_profile_by_vpn_id(vpn_id: str) -> VPNUsers | None:
    async with engine.connect() as conn:
        sql_query = select(VPNUsers).where(VPNUsers.vpn_id == vpn_id)
        result = await conn.execute(sql_query)
        user: VPNUsers | None = result.scalar_one_or_none()
    return user


async def had_test_sub(tg_id: int) -> bool:
    """
    True  – если у пользователя уже был тестовый период.
    False – если записи нет или test = False/0.
    """
    async with engine.connect() as conn:
        sql_query = select(VPNUsers.test).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(sql_query)
        test_flag = result.scalar_one_or_none()

    if test_flag is None:
        return False

    return bool(test_flag)


async def update_test_subscription_state(tg_id: int):
    async with engine.connect() as conn:
        sql_q = (
            update(VPNUsers)
            .where(VPNUsers.tg_id == tg_id)
            .values(test=True)
        )
        await conn.execute(sql_q)
        await conn.commit()


async def add_yookassa_payment(
    tg_id: int,
    callback: str,
    chat_id: int,
    lang_code: str,
    payment_id,
) -> None:
    async with engine.connect() as conn:
        sql_q = insert(YPayments).values(
            tg_id=tg_id,
            payment_id=payment_id,
            chat_id=chat_id,
            callback=callback,
            lang=lang_code,
        )
        await conn.execute(sql_q)
        await conn.commit()


async def add_cryptomus_payment(
    tg_id: int,
    callback: str,
    chat_id: int,
    lang_code: str,
    data,
) -> None:
    async with engine.connect() as conn:
        sql_q = insert(CPayments).values(
            tg_id=tg_id,
            payment_uuid=data["order_id"],
            order_id=data["order_id"],
            chat_id=chat_id,
            callback=callback,
            lang=lang_code,
        )
        await conn.execute(sql_q)
        await conn.commit()


async def get_yookassa_payment(payment_id) -> YPayments | None:
    async with engine.connect() as conn:
        sql_q = select(YPayments).where(YPayments.payment_id == payment_id)
        result = await conn.execute(sql_q)
        payment: YPayments | None = result.scalar_one_or_none()
    return payment


async def get_cryptomus_payment(order_id) -> CPayments | None:
    async with engine.connect() as conn:
        sql_q = select(CPayments).where(CPayments.order_id == order_id)
        result = await conn.execute(sql_q)
        payment: CPayments | None = result.scalar_one_or_none()
    return payment


async def delete_payment(payment_id):
    async with engine.connect() as conn:
        sql_q = delete(YPayments).where(YPayments.payment_id == payment_id)
        await conn.execute(sql_q)
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


async def get_manual_payment(payment_id) -> ManualPayments | None:
    async with engine.connect() as conn:
        sql_q = select(ManualPayments).where(ManualPayments.id == payment_id)
        result = await conn.execute(sql_q)
        payment: ManualPayments | None = result.scalar_one_or_none()
    return payment


async def update_manual_payment(payment_id, **kwargs):
    async with engine.connect() as conn:
        sql_q = (
            update(ManualPayments)
            .where(ManualPayments.id == payment_id)
            .values(**kwargs)
        )
        await conn.execute(sql_q)
        await conn.commit()


async def get_latest_manual_payment_by_status(
    tg_id: int,
    statuses: list[str],
) -> ManualPayments | None:
    async with engine.connect() as conn:
        sql_q = (
            select(ManualPayments)
            .where(
                ManualPayments.tg_id == tg_id,
                ManualPayments.status.in_(statuses),
            )
            .order_by(desc(ManualPayments.id))
            .limit(1)
        )
        result = await conn.execute(sql_q)
        payment: ManualPayments | None = result.scalar_one_or_none()
    return payment
