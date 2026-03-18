from app.models.finance import VoteHead
from app import db

class VoteHeadRepository:
  @staticmethod
  def get_all_active():
    return VoteHead.query.all
  
  @staticmethod
  def update_balance(vote_head_id, amount):
    vote_head = VoteHead.query.get(vote_head_id)
    if vote_head:
      vote_head.current_balance += amount
      db.session.add(vote_head)


 