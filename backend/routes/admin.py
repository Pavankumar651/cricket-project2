"""
Fixed Admin Routes - All pages require login
"""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
def require_login():
    """Every admin page requires authentication."""
    pass


@admin_bp.route('/')
@admin_bp.route('/dashboard')
def dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/team-setup')
def team_setup():
    return render_template('admin/team_setup.html')


@admin_bp.route('/match-setup')
def match_setup():
    return render_template('admin/match_setup.html')


@admin_bp.route('/scoring/<int:match_id>')
def scoring(match_id):
    return render_template('admin/scoring.html', match_id=match_id)