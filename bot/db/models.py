from sqlalchemy import Column, BigInteger, Integer, String, Boolean

from db.base import Base

class VPNUsers(Base):
    __tablename__ = "vpnusers"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger)
    vpn_id = Column(String(64), default="")
    test = Column(Boolean, default=False)

class CPayments(Base):
    __tablename__ = "crypto_payments"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger)
    lang = Column(String(64))
    payment_uuid = Column(String(64))
    order_id = Column(String(64))
    chat_id = Column(BigInteger)
    callback = Column(String(64))

class YPayments(Base):
    __tablename__ = "yookassa_payments"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger)
    lang = Column(String(64))
    payment_id = Column(String(64))
    chat_id = Column(BigInteger)
    callback = Column(String(64))


class ManualPayments(Base):
    __tablename__ = "manual_payments"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger)
    username = Column(String(64))
    lang = Column(String(64))
    chat_id = Column(BigInteger)
    callback = Column(String(64))
    plan_name = Column(String(128))
    amount = Column(String(64))
    status = Column(String(64))
    proof_message_id = Column(BigInteger)
    proof_chat_id = Column(BigInteger)
    admin_message_id = Column(BigInteger)
    admin_chat_id = Column(BigInteger)


class UserLink(Base):
    __tablename__ = "user_links"

    id = Column(BigInteger, primary_key=True, unique=True, autoincrement=True)
    tg_id = Column(BigInteger, index=True, nullable=False)
    tg_username = Column(String(64))
    marzban_user = Column(String(64), index=True, nullable=False, unique=True)
