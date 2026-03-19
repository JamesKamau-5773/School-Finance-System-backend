import africastalking
from flask import current_app


class SMSService:
    @staticmethod
    def send_receipt(phone_number, student_name, amount, balance, reference):
        """
        Sends a professional, automated fee receipt to the parent.
        """
        # Initialize Africa's Talking (Credentials from .env)
        username = current_app.config['AT_USERNAME']
        api_key = current_app.config['AT_API_KEY']
        africastalking.initialize(username, api_key)
        sms = africastalking.SMS

        message = (
            f"Dear Parent, we have received KES {amount} for {student_name}. "
            f"New Balance: KES {balance}. Ref: {reference}. "
            f"Thank you. St. Gerald High School."
        )

        try:
            # Note: 'sender_id' is the Alphanumeric ID (e.g., 'STGERALD')
            response = sms.send(
                message, [phone_number], sender_id=current_app.config['AT_SENDER_ID'])
            return response
        except Exception as e:
            # We log the error but don't fail the transaction if SMS fails
            print(f"SMS Delivery Failed: {str(e)}")
            return None
