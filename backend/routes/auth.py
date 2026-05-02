"""
Fixed Auth Routes - Admin login protection
"""
from flask import Blueprint, request, jsonify, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from backend.models.models import Admin
from backend.app import db, login_manager

auth_bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# Redirect unauthenticated users to login instead of 401
@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Already logged in → go to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))

    error = None
    if request.method == 'POST':
        if request.is_json:
            data     = request.json
            username = data.get('username', '').strip()
            password = data.get('password', '')
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin, remember=True)
            next_url = request.args.get('next') or url_for('admin.dashboard')
            if request.is_json:
                return jsonify({'success': True, 'redirect': next_url})
            return redirect(next_url)

        error = 'Invalid username or password'
        if request.is_json:
            return jsonify({'error': error}), 401

    return render_template('login.html', error=error)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))