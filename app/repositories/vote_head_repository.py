from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models.finance import VoteHead
from app import db

class VoteHeadRepository:
  @staticmethod
  def _to_decimal(value, field_name, default='0'):
    raw = default if value is None else value
    try:
      parsed = Decimal(str(raw))
    except Exception:
      raise ValueError(f"{field_name} must be a valid number")

    if parsed < 0:
      raise ValueError(f"{field_name} cannot be negative")
    return parsed

  @staticmethod
  def _serialize(vote_head):
    return {
      "id": str(vote_head.id),
      "code": vote_head.code,
      "name": vote_head.name,
      "fund_type": vote_head.fund_type,
      "annual_budget": float(vote_head.annual_budget or 0),
      "current_balance": float(vote_head.current_balance or 0)
    }

  @staticmethod
  def get_all_active():
    vote_heads = VoteHead.query.order_by(VoteHead.name.asc()).all()
    return [VoteHeadRepository._serialize(vote_head) for vote_head in vote_heads]

  @staticmethod
  def create(data):
    code = str(data.get('code', '')).strip().upper()
    name = str(data.get('name', '')).strip()
    fund_type = str(data.get('fund_type', 'CAPITATION')).strip().upper()

    if not code:
      raise ValueError('code is required')
    if not name:
      raise ValueError('name is required')

    vote_head = VoteHead(
      code=code,
      name=name,
      fund_type=fund_type,
      annual_budget=VoteHeadRepository._to_decimal(data.get('annual_budget'), 'annual_budget'),
      current_balance=VoteHeadRepository._to_decimal(data.get('current_balance'), 'current_balance')
    )

    try:
      db.session.add(vote_head)
      db.session.commit()
      return VoteHeadRepository._serialize(vote_head)
    except IntegrityError:
      db.session.rollback()
      raise ValueError('vote head code already exists')
    except Exception as e:
      db.session.rollback()
      raise e

  @staticmethod
  def update(vote_head_id, data):
    vote_head = VoteHead.query.get(vote_head_id)
    if not vote_head:
      raise ValueError('vote head not found')

    if 'code' in data:
      code = str(data.get('code', '')).strip().upper()
      if not code:
        raise ValueError('code cannot be empty')
      vote_head.code = code

    if 'name' in data:
      name = str(data.get('name', '')).strip()
      if not name:
        raise ValueError('name cannot be empty')
      vote_head.name = name

    if 'fund_type' in data:
      fund_type = str(data.get('fund_type', '')).strip().upper()
      if not fund_type:
        raise ValueError('fund_type cannot be empty')
      vote_head.fund_type = fund_type

    if 'annual_budget' in data:
      vote_head.annual_budget = VoteHeadRepository._to_decimal(
        data.get('annual_budget'), 'annual_budget'
      )

    if 'current_balance' in data:
      vote_head.current_balance = VoteHeadRepository._to_decimal(
        data.get('current_balance'), 'current_balance'
      )

    try:
      db.session.commit()
      return VoteHeadRepository._serialize(vote_head)
    except IntegrityError:
      db.session.rollback()
      raise ValueError('vote head code already exists')
    except Exception as e:
      db.session.rollback()
      raise e

  @staticmethod
  def delete(vote_head_id):
    vote_head = VoteHead.query.get(vote_head_id)
    if not vote_head:
      raise ValueError('vote head not found')

    try:
      db.session.delete(vote_head)
      db.session.commit()
      return True
    except Exception:
      db.session.rollback()
      raise ValueError('cannot delete vote head with existing transactions')

  @staticmethod
  def update_balance(vote_head_id, amount):
    vote_head = VoteHead.query.get(vote_head_id)
    if vote_head:
      vote_head.current_balance += amount
      db.session.add(vote_head)


 