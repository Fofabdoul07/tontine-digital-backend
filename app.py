from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import uuid

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-changez-moi')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'sqlite:///tontine_dev.db'          # SQLite en local pour tester facilement
).replace('postgres://', 'postgresql://')   # Fix Render.com
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-changez-moi')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

db  = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)   # Autorise les appels depuis l'application React

# ─── MODÈLES (Tables de la base de données) ──────────────────────────────────

class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    phone         = db.Column(db.String(20), unique=True, nullable=False)
    email         = db.Column(db.String(100), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    is_admin      = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'phone': self.phone, 'email': self.email,
            'is_active': self.is_active, 'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Tontine(db.Model):
    __tablename__ = 'tontines'
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    description     = db.Column(db.Text)
    amount          = db.Column(db.Float, nullable=False)   # Cotisation par tour
    frequency       = db.Column(db.String(20), nullable=False)  # Hebdo / Mensuel
    creator_id      = db.Column(db.Integer, db.ForeignKey('users.id'))
    start_date      = db.Column(db.DateTime)
    status          = db.Column(db.String(20), default='active')
    total_collected = db.Column(db.Float, default=0)
    current_tour    = db.Column(db.Integer, default=1)
    total_tours     = db.Column(db.Integer, default=1)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    members         = db.relationship('TontineMember', backref='tontine', lazy=True)

    def to_dict(self):
        creator = User.query.get(self.creator_id)
        return {
            'id': self.id, 'name': self.name,
            'description': self.description,
            'amount': self.amount, 'frequency': self.frequency,
            'status': self.status,
            'total_collected': self.total_collected,
            'current_tour': self.current_tour,
            'total_tours': self.total_tours,
            'member_count': len(self.members),
            'creator': creator.name if creator else 'Inconnu',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TontineMember(db.Model):
    __tablename__ = 'tontine_members'
    id          = db.Column(db.Integer, primary_key=True)
    tontine_id  = db.Column(db.Integer, db.ForeignKey('tontines.id'))
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'))
    tour_number = db.Column(db.Integer)            # Son numéro de tour
    has_paid    = db.Column(db.Boolean, default=False)
    joined_at   = db.Column(db.DateTime, default=datetime.utcnow)
    user        = db.relationship('User', backref='memberships')


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id                    = db.Column(db.Integer, primary_key=True)
    reference             = db.Column(db.String(100), unique=True, nullable=False)
    user_id               = db.Column(db.Integer, db.ForeignKey('users.id'))
    tontine_id            = db.Column(db.Integer, db.ForeignKey('tontines.id'), nullable=True)
    amount                = db.Column(db.Float, nullable=False)
    fee                   = db.Column(db.Float, default=0)
    net_amount            = db.Column(db.Float, nullable=False)
    type                  = db.Column(db.String(20), nullable=False)    # deposit / withdrawal
    status                = db.Column(db.String(20), default='pending') # pending/completed/failed
    payment_method        = db.Column(db.String(20), nullable=False)    # wave/orange/mtn
    sender_phone          = db.Column(db.String(20))
    receiver_phone        = db.Column(db.String(20))
    external_transaction_id = db.Column(db.String(200))
    description           = db.Column(db.Text)
    initiated_at          = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at          = db.Column(db.DateTime)
    error_message         = db.Column(db.Text)

    @staticmethod
    def generate_reference():
        ts  = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        uid = str(uuid.uuid4())[:8].upper()
        return f'TXN-{ts}-{uid}'

    def to_dict(self):
        user = User.query.get(self.user_id)
        tontine = Tontine.query.get(self.tontine_id) if self.tontine_id else None
        return {
            'id': self.id, 'reference': self.reference,
            'user_name': user.name if user else 'Inconnu',
            'tontine': tontine.name if tontine else None,
            'amount': self.amount, 'fee': self.fee,
            'net_amount': self.net_amount,
            'type': self.type, 'status': self.status,
            'payment_method': self.payment_method,
            'sender_phone': self.sender_phone,
            'receiver_phone': self.receiver_phone,
            'description': self.description,
            'initiated_at': self.initiated_at.isoformat() if self.initiated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


# ─── ROUTES : AUTHENTIFICATION ────────────────────────────────────────────────

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data or not data.get('phone') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Nom, téléphone et mot de passe obligatoires'}), 400

    if User.query.filter_by(phone=data['phone']).first():
        return jsonify({'message': 'Ce numéro est déjà utilisé'}), 409

    user = User(name=data['name'], phone=data['phone'], email=data.get('email'))
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=user.id)
    return jsonify({
        'message': 'Inscription réussie !',
        'access_token': token,
        'user': user.to_dict()
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(phone=data.get('phone')).first()

    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'message': 'Numéro ou mot de passe incorrect'}), 401

    token = create_access_token(identity=user.id)
    return jsonify({
        'message': 'Connexion réussie',
        'access_token': token,
        'user': user.to_dict()
    }), 200


@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_me():
    user = User.query.get(get_jwt_identity())
    if not user:
        return jsonify({'message': 'Utilisateur introuvable'}), 404
    return jsonify(user.to_dict()), 200


# ─── ROUTES : TONTINES ───────────────────────────────────────────────────────

@app.route('/api/tontines', methods=['POST'])
@jwt_required()
def create_tontine():
    uid  = get_jwt_identity()
    data = request.get_json()

    tontine = Tontine(
        name        = data['name'],
        description = data.get('description', ''),
        amount      = float(data['amount']),
        frequency   = data['frequency'],
        creator_id  = uid,
        total_tours = int(data.get('total_tours', 1)),
        start_date  = datetime.utcnow()
    )
    db.session.add(tontine)
    db.session.flush()

    # Le créateur devient automatiquement membre (tour 1)
    member = TontineMember(tontine_id=tontine.id, user_id=uid, tour_number=1)
    db.session.add(member)
    db.session.commit()

    return jsonify({'message': 'Tontine créée !', 'tontine': tontine.to_dict()}), 201


@app.route('/api/tontines', methods=['GET'])
@jwt_required()
def get_tontines():
    uid = get_jwt_identity()
    # Tontines créées par l'utilisateur + celles où il est membre
    memberships = TontineMember.query.filter_by(user_id=uid).all()
    tontine_ids = {m.tontine_id for m in memberships}
    created     = Tontine.query.filter_by(creator_id=uid).all()
    for t in created:
        tontine_ids.add(t.id)

    tontines = Tontine.query.filter(Tontine.id.in_(tontine_ids)).all()
    return jsonify([t.to_dict() for t in tontines]), 200


@app.route('/api/tontines/<int:tid>', methods=['GET'])
@jwt_required()
def get_tontine(tid):
    t = Tontine.query.get_or_404(tid)
    data = t.to_dict()
    # Ajouter les membres
    data['members'] = [{
        'id': m.id,
        'user_id': m.user_id,
        'name': m.user.name,
        'phone': m.user.phone,
        'tour_number': m.tour_number,
        'has_paid': m.has_paid
    } for m in t.members]
    return jsonify(data), 200


@app.route('/api/tontines/<int:tid>/join', methods=['POST'])
@jwt_required()
def join_tontine(tid):
    uid = get_jwt_identity()
    t   = Tontine.query.get_or_404(tid)

    if TontineMember.query.filter_by(tontine_id=tid, user_id=uid).first():
        return jsonify({'message': 'Vous êtes déjà membre de cette tontine'}), 409

    next_tour = len(t.members) + 1
    member = TontineMember(tontine_id=tid, user_id=uid, tour_number=next_tour)
    db.session.add(member)
    db.session.commit()
    return jsonify({'message': 'Vous avez rejoint la tontine !'}), 200


@app.route('/api/tontines/<int:tid>', methods=['PATCH'])
@jwt_required()
def update_tontine(tid):
    uid = get_jwt_identity()
    t   = Tontine.query.get_or_404(tid)
    if t.creator_id != uid:
        return jsonify({'message': 'Accès refusé'}), 403

    data = request.get_json()
    if 'status' in data:
        t.status = data['status']
    if 'name' in data:
        t.name = data['name']
    db.session.commit()
    return jsonify({'message': 'Tontine mise à jour', 'tontine': t.to_dict()}), 200


# ─── ROUTES : PAIEMENTS ──────────────────────────────────────────────────────

ADMIN_ACCOUNTS = {
    'wave':   os.getenv('ADMIN_WAVE_NUMBER',   '0747429889'),
    'orange': os.getenv('ADMIN_ORANGE_NUMBER', '0555471974'),
    'mtn':    os.getenv('ADMIN_MTN_NUMBER',    '0747429889'),
}
FEE_RATE = float(os.getenv('SERVICE_FEE_PERCENTAGE', '0.02'))


@app.route('/api/payments/initiate', methods=['POST'])
@jwt_required()
def initiate_payment():
    uid  = get_jwt_identity()
    data = request.get_json()

    method = data.get('payment_method', '').lower()
    if method not in ADMIN_ACCOUNTS:
        return jsonify({'message': 'Méthode de paiement invalide (wave/orange/mtn)'}), 400

    amount     = float(data['amount'])
    fee        = round(amount * FEE_RATE, 2)
    net_amount = amount - fee
    admin_num  = ADMIN_ACCOUNTS[method]

    txn = Transaction(
        reference      = Transaction.generate_reference(),
        user_id        = uid,
        tontine_id     = data.get('tontine_id'),
        amount         = amount,
        fee            = fee,
        net_amount     = net_amount,
        type           = 'deposit',
        status         = 'processing',
        payment_method = method,
        sender_phone   = data.get('phone_number', ''),
        receiver_phone = admin_num,
        description    = data.get('description', 'Cotisation tontine')
    )
    db.session.add(txn)
    db.session.flush()

    # ── En production : appeler ici l'API Wave / Orange / MTN ──
    # Pour l'instant on simule le succès
    txn.status       = 'completed'
    txn.completed_at = datetime.utcnow()

    # Mettre à jour la cagnotte de la tontine
    if txn.tontine_id:
        t = Tontine.query.get(txn.tontine_id)
        if t:
            t.total_collected += amount
            # Marquer le membre comme payé
            m = TontineMember.query.filter_by(
                tontine_id=txn.tontine_id, user_id=uid
            ).first()
            if m:
                m.has_paid = True

    db.session.commit()

    return jsonify({
        'message'       : f'Paiement réussi ! Transféré vers {admin_num}',
        'reference'     : txn.reference,
        'amount'        : amount,
        'fee'           : fee,
        'net_amount'    : net_amount,
        'admin_account' : admin_num,
        'method'        : method.upper(),
        'status'        : 'completed'
    }), 200


@app.route('/api/payments/history', methods=['GET'])
@jwt_required()
def payment_history():
    uid = get_jwt_identity()
    txns = Transaction.query.filter_by(user_id=uid)\
           .order_by(Transaction.initiated_at.desc()).all()
    return jsonify([t.to_dict() for t in txns]), 200


# ─── ROUTES : ADMIN ──────────────────────────────────────────────────────────

@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def admin_stats():
    total_amount = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter_by(status='completed').scalar() or 0

    return jsonify({
        'total_users'       : User.query.count(),
        'total_tontines'    : Tontine.query.count(),
        'active_tontines'   : Tontine.query.filter_by(status='active').count(),
        'total_transactions': Transaction.query.count(),
        'total_amount'      : float(total_amount),
        'admin_accounts'    : ADMIN_ACCOUNTS,
        'fee_rate'          : FEE_RATE
    }), 200


@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@app.route('/api/admin/tontines', methods=['GET'])
@jwt_required()
def admin_tontines():
    tontines = Tontine.query.order_by(Tontine.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tontines]), 200


@app.route('/api/admin/transactions', methods=['GET'])
@jwt_required()
def admin_transactions():
    limit = request.args.get('limit', 50, type=int)
    txns  = Transaction.query.order_by(Transaction.initiated_at.desc()).limit(limit).all()
    return jsonify([t.to_dict() for t in txns]), 200


@app.route('/api/admin/users/<int:uid>/toggle', methods=['PATCH'])
@jwt_required()
def toggle_user(uid):
    user = User.query.get_or_404(uid)
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify({'message': 'Statut mis à jour', 'is_active': user.is_active}), 200


# ─── ROUTE DE SANTÉ ──────────────────────────────────────────────────────────

@app.route('/')
@app.route('/health')
def health():
    return jsonify({
        'status' : 'OK ✅',
        'app'    : 'Tontine Digital API',
        'version': '1.0.0',
        'admin_accounts': ADMIN_ACCOUNTS
    }), 200


# ─── DÉMARRAGE ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Base de données prête")
        print("🚀 API Tontine Digital démarrée sur http://localhost:5000")
        for k, v in ADMIN_ACCOUNTS.items():
            print(f"   📱 {k.upper()}: {v}")
    app.run(host='0.0.0.0', port=5000, debug=True)
