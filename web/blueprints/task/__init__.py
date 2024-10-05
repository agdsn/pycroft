import typing as t
from dataclasses import asdict
from typing import NoReturn

from flask import Blueprint, url_for, abort, flash, redirect, request, render_template
from flask.typing import ResponseValue
from flask_login import current_user
from sqlalchemy import select

from pycroft.exc import PycroftException
from pycroft.lib.task import cancel_task, task_type_to_impl, \
    manually_execute_task, reschedule_task
from pycroft.model import session
from pycroft.model.facilities import Building
from pycroft.model.task import Task, TaskStatus, UserTask
from web.blueprints import redirect_or_404
from web.blueprints.access import BlueprintAccess
from web.blueprints.helpers.user import get_user_or_404
from web.blueprints.navigation import BlueprintNavigation
from web.blueprints.task.forms import RescheduleTaskForm
from web.blueprints.task.tables import TaskTable, TaskRow
from web.table.table import (
    BtnColResponse,
    TableResponse,
    datetime_format,
    LinkColResponse,
)
from web.template_filters import datetime_filter

bp = Blueprint('task', __name__)
access = BlueprintAccess(bp, required_properties=['user_show'])
nav = BlueprintNavigation(bp, "Tasks", icon='fa-tasks', blueprint_access=access)


def format_parameters[T: t.MutableMapping[str, t.Any]](parameters: T) -> T:
    """Make task parameters human readable by looking up objects behind ids"""

    # Replace building_id by the buildings short name
    if bid := parameters.get("building_id"):
        if building := session.session.get(Building, bid):
            parameters["building"] = building.short_name
            del parameters["building_id"]
    return parameters


def task_row(task: UserTask) -> TaskRow:
    task_impl = task_type_to_impl.get(task.type)
    return TaskRow(
        id=task.id,
        user=LinkColResponse(
            href=url_for('user.user_show', user_id=task.user.id),
            title=task.user.name
        ),
        name=task_impl.name,
        type=task.type.name,  # actually redundant, because we assume UserTask
        status=task.status.name,
        parameters=format_parameters(asdict(task.parameters)),
        errors=task.errors if task.errors is not None else list(),
        due=datetime_format(task.due, default="", formatter=datetime_filter),
        created=f"{task.created:%Y-%m-%d %H:%M:%S}",
        creator=LinkColResponse(
            href=url_for('user.user_show', user_id=task.creator.id),
            title=task.creator.name
        ),
        actions=[
            BtnColResponse(
                href=url_for(
                    '.cancel_user_task',
                    task_id=task.id,
                    redirect=url_for('user.user_show', user_id=task.user.id, _anchor='tasks')
                ),
                title="Abbrechen",
                icon='fa-times',
                btn_class='btn-link'
            ),
            BtnColResponse(
                href=url_for(
                    '.reschedule_user_task',
                    task_id=task.id,
                    redirect=url_for('user.user_show', user_id=task.user.id, _anchor='tasks')
                ),
                title="Datum Ändern",
                icon='fa-calendar-alt',
                btn_class='btn-link'
            ),
            BtnColResponse(
                href=url_for(
                    '.manually_execute_user_task',
                    task_id=task.id,
                    redirect=url_for('user.user_show', user_id=task.user.id, _anchor='tasks')
                ),
                title="Sofort ausführen",
                icon="fa-fast-forward",
                btn_class="btn-link",
            ),
        ]
        if task.status == TaskStatus.OPEN
        else [],
    )


@bp.route("/user/<int:user_id>/json")
def json_tasks_for_user(user_id: int) -> ResponseValue:
    user = get_user_or_404(user_id)
    return TableResponse[TaskRow](
        items=[task_row(t.cast(UserTask, task)) for task in user.tasks]
    ).model_dump()


@bp.route("/user/json")
def json_user_tasks() -> ResponseValue:
    failed_only = bool(request.args.get("failed_only", False))
    open_only = bool(request.args.get("open_only", False))

    tasks = select(Task).order_by(Task.status.desc(), Task.due.asc())

    if failed_only:
        tasks = tasks.filter_by(status=TaskStatus.FAILED)
    elif open_only:
        tasks = tasks.filter_by(status=TaskStatus.OPEN)
    else:
        tasks = tasks

    return TableResponse[TaskRow](
        items=[
            task_row(t.cast(UserTask, task)) for task in session.session.scalars(tasks)
        ]
    ).model_dump()


def get_task_or_404(task_id: int) -> Task | NoReturn:
    if task := session.session.get(Task, task_id):
        return task
    abort(404)


@bp.route("/<int:task_id>/manually_execute")
@access.require('user_change')
def manually_execute_user_task(task_id: int) -> ResponseValue:
    task = get_task_or_404(task_id)
    try:
        manually_execute_task(task, processor=current_user)
        session.session.commit()
    except Exception as e:
        if not isinstance(e, PycroftException):
            import logging
            logging.getLogger('pycroft.web').error(
                "Unexpected error in manual task execution: %s", e,
                exc_info=True
            )
        flash(f"Fehler bei der Ausführung: {e}", 'error')
        session.session.rollback()
    else:
        flash("Aufgabe erfolgreich ausgeführt", 'success')

    return redirect_or_404(request.args.get("redirect"))


@bp.route("/<int:task_id>/cancel")
@access.require('user_change')
def cancel_user_task(task_id: int) -> ResponseValue:
    task = get_task_or_404(task_id)

    cancel_task(task, current_user)
    session.session.commit()

    flash('Aufgabe erfolgreich abgebrochen.', 'success')
    return redirect_or_404(request.args.get("redirect"))


@bp.route("/<int:task_id>/reschedule", methods=['GET', 'POST'])
@access.require('user_change')
def reschedule_user_task(task_id: int) -> ResponseValue:
    task = get_task_or_404(task_id)

    form = RescheduleTaskForm()
    assert isinstance(task, UserTask)
    return_url = url_for('user.user_show', user_id=task.user.id, _anchor='tasks')

    if form.validate_on_submit():
        reschedule_task(task, form.full_datetime, processor=current_user)
        session.session.commit()
        flash(f'Datum erfolgreich auf {form.full_datetime} geändert.', 'success')
        return redirect(return_url)

    return render_template(
        "task/reschedule_task.html",
        form_args={'form': form, 'cancel_to': return_url}
    )



@bp.route("/user")
@nav.navigate("Tasks")
def user_tasks() -> ResponseValue:
    return render_template(
        "task/tasks.html",
        task_table=TaskTable(data_url=url_for('.json_user_tasks', open_only=1)),
        task_failed_table=TaskTable(data_url=url_for('.json_user_tasks', failed_only=1),
                                    sort_order='desc'),
        page_title="Aufgaben (Nutzer)"
    )
