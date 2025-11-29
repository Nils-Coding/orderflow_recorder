from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Numeric, String, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
	pass


class FuturesTrade(Base):
	__tablename__ = "futures_trades"

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
	event_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
	trade_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=True)
	price: Mapped["Numeric"] = mapped_column(Numeric(38, 18), nullable=False)
	quantity: Mapped["Numeric"] = mapped_column(Numeric(38, 18), nullable=False)
	is_buyer_maker: Mapped[bool] = mapped_column(Boolean, nullable=False)
	agg_trade_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
	ingest_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	__table_args__ = (
		UniqueConstraint("symbol", "agg_trade_id", name="uq_trades_symbol_aggid"),
	)


class FuturesOrderbookUpdate(Base):
	__tablename__ = "futures_orderbook_updates"

	id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
	symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
	event_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
	first_update_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
	final_update_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
	bids: Mapped[dict] = mapped_column(JSONB, nullable=False)
	asks: Mapped[dict] = mapped_column(JSONB, nullable=False)
	ingest_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	__table_args__ = (
		Index("ix_orderbook_symbol_final_u", "symbol", "final_update_id"),
	)


