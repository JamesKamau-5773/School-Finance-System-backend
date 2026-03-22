from app import db
from app.models.fee_structure import FeeStructure

class FeeRepository:
    @staticmethod
    def create_fee_structure(data):
        """Saves a new BOM-approved levy to the database."""
        try:
            new_fee = FeeStructure(**data)
            db.session.add(new_fee)
            db.session.commit()
            return new_fee
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_all_active_fees(academic_year=None, term=None):
        """Fetches active levies, optionally filtered by year and term."""
        try:
            query = FeeStructure.query.filter_by(is_active=True)
            
            if academic_year:
                query = query.filter_by(academic_year=academic_year)
            if term:
                query = query.filter_by(term=term)
                
            # Order by newest first
            return query.order_by(FeeStructure.created_at.desc()).all()
        except Exception as e:
            raise e