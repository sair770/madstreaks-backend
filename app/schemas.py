"""
Pydantic schemas for request validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class TradeCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    entry_price: float = Field(..., gt=0)
    target_price: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    quantity: int = Field(..., gt=0)
    trade_type: Optional[str] = Field("long", pattern="^(long|short)$")
    status: Optional[str] = Field("pending", pattern="^(pending|open|closed)$")
    notes: Optional[str] = Field(None, max_length=500)


class TradeUpdate(BaseModel):
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    entry_price: Optional[float] = Field(None, gt=0)
    target_price: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, pattern="^(pending|open|closed)$")
    exit_price: Optional[float] = Field(None, gt=0)
    pnl: Optional[float] = None
    notes: Optional[str] = Field(None, max_length=500)


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    alert_type: str = Field(..., pattern="^(above|below|pct_change)$")
    target_price: Optional[float] = Field(None, gt=0)
    pct_change: Optional[float] = Field(None, gt=0)
    base_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = Field(True)
    notify_telegram: Optional[bool] = Field(True)
    repeat_mode: Optional[str] = Field("one_shot", pattern="^(one_shot|repeating)$")
    notes: Optional[str] = Field(None, max_length=500)


class AlertUpdate(BaseModel):
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    alert_type: Optional[str] = Field(None, pattern="^(above|below|pct_change)$")
    target_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class BriefingAlert(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    alert_type: str = Field(..., pattern="^(above|below|pct_change)$")
    target_price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)


