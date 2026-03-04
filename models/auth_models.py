"""
Authentication and authorisation models.

User          – application user with username/password (bcrypt hashed).
TeamPermission – maps a user to a team (category) with a role.

Roles (ordered by privilege):
  'viewer'  – read-only access to games & stats for the assigned team(s)
  'editor'  – read + write access to games for the assigned team(s)
  'admin'   – full access (same as is_admin=True on User)

A User with is_admin=True is implicitly an admin for *all* teams.
A TeamPermission with category='*' grants the specified role to *all* teams.
"""
from datetime import datetime, timezone
from .database import db


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    is_admin = db.Column(db.Integer, default=0, nullable=False)  # 0/1
    created_at = db.Column(db.Text, nullable=False,
                           default=lambda: datetime.now(timezone.utc).isoformat())

    permissions = db.relationship('TeamPermission', backref='user',
                                  cascade='all, delete-orphan', lazy=True)

    def set_password(self, plaintext: str) -> None:
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(plaintext)

    def check_password(self, plaintext: str) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, plaintext)

    # ── Role helpers ──────────────────────────────────────────────────────

    def has_role(self, category: str, required_role: str) -> bool:
        """Return True if this user has *at least* required_role for category.

        Role hierarchy (lowest to highest): viewer < editor < admin.
        Admin users always pass, regardless of TeamPermission rows.
        """
        if self.is_admin:
            return True
        HIERARCHY = {'viewer': 0, 'editor': 1, 'admin': 2}
        required_level = HIERARCHY.get(required_role, 0)
        for perm in self.permissions:
            if perm.category in (category, '*'):
                if HIERARCHY.get(perm.role, -1) >= required_level:
                    return True
        return False

    def get_role(self, category: str) -> str | None:
        """Return the highest role this user has for *category*, or None."""
        if self.is_admin:
            return 'admin'
        HIERARCHY = {'viewer': 0, 'editor': 1, 'admin': 2}
        best = None
        best_level = -1
        for perm in self.permissions:
            if perm.category in (category, '*'):
                level = HIERARCHY.get(perm.role, -1)
                if level > best_level:
                    best_level = level
                    best = perm.role
        return best

    def accessible_categories(self) -> list[str]:
        """Return list of team categories this user can access (viewers+)."""
        if self.is_admin:
            return ['*']
        return list({p.category for p in self.permissions})

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': bool(self.is_admin),
            'created_at': self.created_at,
            'permissions': [p.to_dict() for p in self.permissions],
        }


class TeamPermission(db.Model):
    __tablename__ = 'team_permissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.Text, nullable=False)   # team category or '*'
    role = db.Column(db.Text, nullable=False)        # viewer / editor / admin

    __table_args__ = (
        db.UniqueConstraint('user_id', 'category', name='uq_user_category'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category': self.category,
            'role': self.role,
        }
