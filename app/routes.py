import os
    db.session.add(recommendation)
    db.session.commit()

    return jsonify({
        'message': 'Recommendation added successfully'
    })


# =====================================================
# ADMIN PAGE
# =====================================================


@app.route('/admin')
@login_required
def admin_panel():

    if not current_user.is_admin:
        flash('Admin access only')
        return redirect(url_for('home'))

    recommendations = db.session.scalars(
        sa.select(Recommendation)
        .order_by(Recommendation.id.desc())
    ).all()

    users = db.session.scalars(
        sa.select(User)
    ).all()

    return render_template(
        'admin.html',
        recommendations=recommendations,
        users=users
    )


@app.route('/admin/delete/<int:id>')
@login_required
def admin_delete(id):

    if not current_user.is_admin:
        return redirect(url_for('home'))

    recommendation = db.session.get(Recommendation, id)

    if recommendation:
        db.session.delete(recommendation)
        db.session.commit()

    flash('Recommendation deleted')

    return redirect(url_for('admin_panel'))
