from app.models.auth import User
from flask_jwt_extended import create_access_token
import bcrypt


class AuthService:
    @staticmethod
    def login_user(full_name, password):
        # 1. Find the user in the database
        user = User.query.filter_by(full_name=full_name).first()

        if not user:
            return {"error": "Invalid credentials"}, 401

        # 2. Check the password against the stored hash
        if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            # 3. Create a JWT token that includes the user's role
            # This allows the frontend to know if this is a 'Principal' or 'Clerk'
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={"role": user.role.name}
            )
            return {
                "message": "Login successful",
                "access_token": access_token,
                "role": user.role.name
            }, 200

        return {"error": "Invalid login credentials"}, 401
