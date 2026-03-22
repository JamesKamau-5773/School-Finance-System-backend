from app.repositories.fee_repository import FeeRepository


class FeeService:
    @staticmethod
    def create_levy(name, amount, academic_year, term, target_cohort, created_by):
        """
        Prepares the payload for a new fee structure.
        """
        data = {
            "name": name,
            "amount": amount,
            "academic_year": academic_year,
            "term": term,
            "target_cohort": target_cohort,
            "created_by": created_by
        }

        fee = FeeRepository.create_fee_structure(data)
        return fee.to_dict()

    @staticmethod
    def get_levies(academic_year=None, term=None):
        """
        Retrieves and formats active fee structures for the frontend.
        """
        fees = FeeRepository.get_all_active_fees(academic_year, term)
        return [fee.to_dict() for fee in fees]
