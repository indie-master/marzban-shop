import hashlib

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import insert, select, update, delete, desc

from db.models import YPayments, CPayments, VPNUsers, ManualPayments
import glv

engine = create_async_engine(glv.config["DB_URL"])


async def create_vpn_profile(tg_id: int):
    async with engine.connect() as conn:
        # проверяем, есть ли уже запись
        stmt = select(VPNUsers).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(stmt)
        existing: VPNUsers | None = result.scalar_one_or_none()
        if existing is not None:
            return

        # лёгкая обфускация: sw_<10 символов md5(tg_id + соль)>
        salt = glv.config.get("SHOP_NAME", "swiftlessvpn")
        seed = f"{tg_id}:{salt}"
        hash_part = hashlib.md5(seed.encode()).hexdigest()[:10]
        username = f"sw_{hash_part}"

        stmt = insert(VPNUsers).values(tg_id=tg_id, vpn_id=username)
        await conn.execute(stmt)
        await conn.commit()



async def get_marzban_profile_db(tg_id: int) -> VPNUsers | None:
    """Вернуть объект с полями vpn_id / tg_id / test по tg_id."""
    async with engine.connect() as conn:
        # Если VPNUsers – Table, у него есть .c, иначе используем атрибут tg_id
        column_tg_id = VPNUsers.c.tg_id if hasattr(VPNUsers, "c") else VPNUsers.tg_id
        stmt = select(VPNUsers).where(column_tg_id == tg_id)
        result = await conn.execute(stmt)
        row = result.first()

    if row is None:
        return None

    m = row._mapping

    # Вариант с ORM: в маппинге лежит сам объект под ключом VPNUsers
    if VPNUsers in m:
        return m[VPNUsers]

    # Вариант с Core: в маппинге лежат отдельные столбцы (id, tg_id, vpn_id, test, ...)
    class _SimpleVPNUser:
        __slots__ = ("id", "tg_id", "vpn_id", "test")

        def __init__(self, mapping):
            # keys: 'id', 'tg_id', 'vpn_id', 'test' – имена столбцов в таблице
            self.id = mapping.get("id")
            self.tg_id = mapping.get("tg_id")
            self.vpn_id = mapping.get("vpn_id")
            self.test = mapping.get("test")

    return _SimpleVPNUser(m)


async def get_marzban_profile_by_vpn_id(vpn_id: str) -> VPNUsers | None:
    """Вернуть объект с полями vpn_id / tg_id / test по vpn_id."""
    async with engine.connect() as conn:
        column_vpn_id = VPNUsers.c.vpn_id if hasattr(VPNUsers, "c") else VPNUsers.vpn_id
        stmt = select(VPNUsers).where(column_vpn_id == vpn_id)
        result = await conn.execute(stmt)
        row = result.first()

    if row is None:
        return None

    m = row._mapping

    if VPNUsers in m:
        return m[VPNUsers]

    class _SimpleVPNUser:
        __slots__ = ("id", "tg_id", "vpn_id", "test")

        def __init__(self, mapping):
            self.id = mapping.get("id")
            self.tg_id = mapping.get("tg_id")
            self.vpn_id = mapping.get("vpn_id")
            self.test = mapping.get("test")

    return _SimpleVPNUser(m)



async def had_test_sub(tg_id: int) -> bool:
    """Был ли уже тестовый период у пользователя."""
    async with engine.connect() as conn:
        stmt = select(VPNUsers.test).where(VPNUsers.tg_id == tg_id)
        result = await conn.execute(stmt)
        value = result.scalar_one_or_none()

    # если записи нет или test = NULL
    if value is None:
        return False

    # value уже скаляр (0/1 или True/False)
    return bool(value)


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
    tg_id: int, callback: str, chat_id: int, lang_code: str, payment_id
) -> dict:
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
    tg_id: int, callback: str, chat_id: int, lang_code: str, data
) -> dict:
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


async def get_yookassa_payment(payment_id) -> YPayments:
    async with engine.connect() as conn:
        sql_q = select(YPayments).where(YPayments.payment_id == payment_id)
        result = await conn.execute(sql_q)
        payment: YPayments = result.scalars().first()
    return payment


async def get_cryptomus_payment(order_id) -> CPayments:
    async with engine.connect() as conn:
        sql_q = select(CPayments).where(CPayments.order_id == order_id)
        result = await conn.execute(sql_q)
        payment: CPayments = result.scalars().first()
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
