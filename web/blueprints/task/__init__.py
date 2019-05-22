import json

from flask import Blueprint, jsonify, url_for, abort, flash, redirect, request, \
    render_template
from flask_login import current_user

from pycroft.model import session

from pycroft.lib.task import cancel_task, task_type_to_impl
from pycroft.model.facilities import Building
from pycroft.model.task import Task, TaskStatus

from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.table import datetime_format
from web.blueprints.helpers.user import get_user_or_404
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.task.tables import TaskTable

bp = Blueprint('task', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])
nav = BlueprintNavigation(bp, "Aufgaben", blueprint_access=access)


def format_parameters(parameters):
    """
    Makes parameters human readable
    """

    # Replace building_id by the buildings short name
    if parameters.get("building_id"):
        building = Building.q.get(parameters["building_id"])

        if building:
            parameters["building"] = building.short_name
            del parameters["building_id"]

    return parameters


def task_object(task):
    task_impl = task_type_to_impl.get(task.type)

    return {
        "id": task.id,
        "user": {
            'href': url_for('user.user_show', user_id=task.user.id),
            'title': task.user.name},
        "name": task_impl.name,
        "type": task.type.name,
        "status": task.status.name,
        "parameters": format_parameters(task.parameters.data),
        "errors": json.loads(task.errors) if task.errors else list(),
        "due": datetime_format(task.due, default=''),
        "creator": {
            'href': url_for('user.user_show', user_id=task.creator.id),
            'title': task.creator.name},
        'actions': [{'href': url_for('.cancel_user_task',
                                     task_id=task.id,
                                     redirect=url_for('user.user_show',
                                                      user_id=task.user.id,
                                                      _anchor='tasks')),
                     'title': "Abbrechen",
                     'icon': 'glyphicon-remove',
                     'btn-class': 'btn-link'}] if task.status == TaskStatus.OPEN else None,
    }

@bp.route("/user/<int:user_id>/json")
def json_tasks_for_user(user_id):
    user = get_user_or_404(user_id)

    return jsonify(items=[task_object(task) for task in user.tasks])


@bp.route("/user/json")
def json_user_tasks():
    tasks = Task.q.order_by(Task.status.desc(), Task.due.asc()).all()

    return jsonify(items=[task_object(task) for task in tasks])


@bp.route("/<int:task_id>/cancel")
@access.require('user_change')
def cancel_user_task(task_id):
    redirect_url = request.args.get("redirect")

    task = Task.q.get(task_id)

    if task is None:
        abort(404)

    cancel_task(task, current_user)

    session.session.commit()

    flash(u'Aufgabe erfolgreich abgebrochen.', 'success')

    if redirect_url:
        return redirect(redirect_url)
    else:
        return abort(404)  # redirect(url_for('.tasks'))


@bp.route("/user")
@nav.navigate("Aufgaben")
def user_tasks():
    return render_template("task/tasks.html",
                           task_table=TaskTable(
                               data_url=url_for('.json_user_tasks')),
                           page_title="Aufgaben (Nutzer)")
