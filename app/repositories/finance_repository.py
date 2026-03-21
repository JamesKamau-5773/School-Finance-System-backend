from sqlalchemy import func
from app import db
from app.models.finance import Transaction, LedgerEntry, VoteHead
from app.utils.validators import is_valid_uuid
from datetime import datetime, timezone


class FinanceRepository:
    @staticmethod
    def _build_vote_head_code(identifier):
        base = ''.join(char if char.isalnum()
                       else '_' for char in str(identifier).upper())
        base = base.strip('_') or 'VH_AUTO'
        code = base[:20]

        if not VoteHead.query.filter_by(code=code).first():
            return code

        suffix = 1
        while True:
            candidate = f"{base[:16]}{suffix:04d}"[:20]
            if not VoteHead.query.filter_by(code=candidate).first():
                return candidate
            suffix += 1

    @staticmethod
    def _resolve_vote_head(identifier):
        if identifier is None:
            return None

        identifier_str = str(identifier)
        if is_valid_uuid(identifier_str):
            return VoteHead.query.filter_by(id=identifier_str).first()

        # Try exact code match first
        by_code = VoteHead.query.filter_by(code=identifier_str).first()
        if by_code:
            return by_code
        
        # Try exact name match
        by_name = VoteHead.query.filter_by(name=identifier_str).first()
        if by_name:
            return by_name
        
        # Try with underscores converted to spaces
        normalized_name = identifier_str.replace('_', ' ')
        if normalized_name != identifier_str:
            by_normalized = VoteHead.query.filter_by(name=normalized_name).first()
            if by_normalized:
                return by_normalized
        
        return None

    @staticmethod
    def _get_or_create_vote_head(identifier, fund_type='CAPITATION'):
        if identifier is None:
            return None

        vote_head = FinanceRepository._resolve_vote_head(identifier)
        if vote_head:
            return vote_head

        identifier_str = str(identifier)
        if is_valid_uuid(identifier_str):
            return None

        vote_head = VoteHead(
            code=FinanceRepository._build_vote_head_code(identifier_str),
            name=identifier_str.replace('_', ' '),
            fund_type=fund_type,
            annual_budget=0,
            current_balance=0
        )
        db.session.add(vote_head)
        db.session.flush()
        return vote_head

    @staticmethod
    def create_transaction_with_ledger(transaction_data, ledger_lines):
        try:
            source_vote_head = FinanceRepository._get_or_create_vote_head(
                transaction_data.get('source_vote_head'))
            destination_vote_head = FinanceRepository._get_or_create_vote_head(
                transaction_data.get('destination_vote_head'))

            if not source_vote_head:
                raise ValueError('source_vote_head is invalid or not found')
            if not destination_vote_head:
                raise ValueError(
                    'destination_vote_head is invalid or not found')

            transaction = Transaction(
                vote_head_id=destination_vote_head.id,
                recorded_by=transaction_data.get('recorded_by'),
                student_id=transaction_data.get('student_id'),
                transaction_type=transaction_data.get(
                    'transaction_type', 'ADJUSTMENT'),
                amount=transaction_data.get('amount'),
                reference_number=transaction_data.get('reference_no'),
                description=transaction_data.get('description'),
                transaction_date=datetime.now(timezone.utc)
            )
            db.session.add(transaction)
            db.session.flush()

            for line in ledger_lines:
                account_name = str(line.get('account_name', ''))
                vote_head_identifier = account_name.replace(
                    'Income_VoteHead_', '', 1)
                vote_head = FinanceRepository._get_or_create_vote_head(
                    vote_head_identifier)

                if not vote_head:
                    raise ValueError(
                        f'Unable to resolve vote head for ledger line: {account_name}')

                ledger_entry = LedgerEntry(
                    transaction_id=transaction.id,
                    vote_head_id=vote_head.id,
                    student_id=transaction_data.get('student_id'),
                    entry_type=line.get('entry_type'),
                    amount=line.get('amount'),
                    payment_method=transaction_data.get('payment_method'),
                    reference_no=transaction_data.get('reference_no'),
                    description=transaction_data.get('description'),
                    created_by=transaction_data.get('recorded_by')
                )
                db.session.add(ledger_entry)

            db.session.commit()
            return transaction
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_dashboard_summary():
        """
        Calculates aggregate financial totals directly in PostgreSQL.
        """
        try:
            total_income = (
                db.session.query(func.sum(Transaction.amount))
                .filter(Transaction.transaction_type == 'INCOME')
                .scalar()
                or 0
            )

            total_expense = (
                db.session.query(func.sum(Transaction.amount))
                .filter(Transaction.transaction_type == 'EXPENSE')
                .scalar()
                or 0
            )

            return {
                "total_collections": float(total_income),
                "total_expenses": float(total_expense),
                "net_position": float(total_income - total_expense)
            }
        except Exception as e:
            raise e

    @staticmethod
    def get_all_vote_heads():
        """
        Fetches all vote heads with their current balances calculated from ledger entries.
        Deduplicates by name to return only one entry per unique vote head.
        
        Balance calculation: Sum of CREDIT entries minus sum of DEBIT entries for each vote head.
        CREDIT = money received, DEBIT = money allocated/spent
        """
        try:
            vote_heads = VoteHead.query.all()
            
            # Calculate balances from ledger entries for each vote head
            ledger_balances = {}
            ledger_entries = LedgerEntry.query.all()
            
            for entry in ledger_entries:
                vh_id = entry.vote_head_id
                if vh_id not in ledger_balances:
                    ledger_balances[vh_id] = {'credits': 0.0, 'debits': 0.0}
                
                amount = float(entry.amount) if entry.amount else 0.0
                if entry.entry_type == 'CREDIT':
                    ledger_balances[vh_id]['credits'] += amount
                elif entry.entry_type == 'DEBIT':
                    ledger_balances[vh_id]['debits'] += amount
            
            # Deduplicate by name, keeping the first entry for each unique name
            seen_names = set()
            result = []
            for vh in vote_heads:
                if vh.name not in seen_names:
                    seen_names.add(vh.name)
                    
                    # Calculate net balance (credits - debits)
                    balance_data = ledger_balances.get(vh.id, {'credits': 0.0, 'debits': 0.0})
                    net_balance = balance_data['credits'] - balance_data['debits']
                    
                    result.append({
                        "id": str(vh.id),
                        "code": vh.code,
                        "name": vh.name,
                        "fund_type": vh.fund_type,
                        "annual_budget": float(vh.annual_budget),
                        "current_balance": net_balance
                    })
            return result
        except Exception as e:
            raise e
    @staticmethod
    def get_trial_balance():
        """
        Generates a formal Trial Balance by calculating the net balance of every account.
        Total Debits MUST equal Total Credits.
        """
        try:
            # 1. Sum all debits and credits grouped by account name
            results = db.session.query(
                LedgerEntry.account_name,
                LedgerEntry.entry_type,
                func.sum(LedgerEntry.amount)
            ).group_by(LedgerEntry.account_name, LedgerEntry.entry_type).all()

            # 2. Process into a working dictionary
            accounts = {}
            for account, entry_type, total in results:
                if account not in accounts:
                    accounts[account] = {'debit': 0.0, 'credit': 0.0}

                if entry_type == 'DEBIT':
                    accounts[account]['debit'] += float(total)
                elif entry_type == 'CREDIT':
                    accounts[account]['credit'] += float(total)

            # 3. Calculate the NET balance for each account (standard accounting practice)
            tb_lines = []
            for acc, data in accounts.items():
                net = data['debit'] - data['credit']
                # If net is positive, it has a Debit balance. If negative, a Credit balance.
                if net > 0:
                    tb_lines.append(
                        {'account': acc, 'debit': net, 'credit': 0.0})
                elif net < 0:
                    tb_lines.append(
                        {'account': acc, 'debit': 0.0, 'credit': abs(net)})
                else:
                    # Account is zeroed out, skip or show zero
                    pass

            # 4. Calculate Grand Totals
            net_total_debit = sum(line['debit'] for line in tb_lines)
            net_total_credit = sum(line['credit'] for line in tb_lines)

            # Sort alphabetically by account name for a clean report
            tb_lines.sort(key=lambda x: x['account'])

            return {
                "lines": tb_lines,
                "totals": {
                    "debit": net_total_debit,
                    "credit": net_total_credit,
                    # Precision rounding to handle floating point math anomalies
                    "is_balanced": round(net_total_debit, 2) == round(net_total_credit, 2)
                }
            }
        except Exception as e:
            raise e
