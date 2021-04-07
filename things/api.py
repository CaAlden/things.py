# -*- coding: utf-8 -*-

"""
Module implementing Things API.
"""

__version__ = "0.0.6"

import os
from shlex import quote
import sys
from typing import List, Dict

from .database import Database


# --------------------------------------------------
# Core functions
# --------------------------------------------------


def tasks(uuid=None, include_items=False, **kwargs):  # noqa: C901
    """
    Read tasks into dicts.

    Note: "task" is a technical term used in the database to refer to a
    to-do, project, or heading. For details, check the "type"-parameter.

    Per default, only tasks marked as incomplete are included. If you
    want to include completed or canceled tasks in the result, check the
    "status"-parameter.

    Parameters
    ----------
    uuid : str or None, optional
        Any valid task uuid. If None, then return all tasks matched.

    include_items : boolean, default False
        Include items contained within a task. These might include
        checklist items, headings, and to-dos.

    type : {'to-do', 'heading', 'project', None}, optional
        Only return a specific type of task:

        'to-do':    may have a checklist; may be in an area and have tags.
        'project':  may have to-dos and headings; may be in an area and
                    have tags.
        'heading':  part of a project; groups tasks.
         None:      return all types of tasks.

    status : {'incomplete', 'completed', 'canceled', None}, optional, \
        default 'incomplete'

        Only include tasks matching that status. If the argument is `None`,
        then include tasks with any status value.

    start : {'Inbox', 'Anytime', 'Someday', None}, optional
        Only include tasks matching that start value. If the argument is
        `None` (default), then include tasks with any start value.

    area : str, bool, or None, optional
        Any valid uuid of an area. Only include tasks matching that area.
        If the argument is `False`, only include tasks _without_ an area.
        If the argument is `True`, only include tasks _with_ an area.
        If the argument is `None` (default), then include all tasks.

    project : str or None, optional
        Any valid uuid of a project. Only include tasks matching that project.
        If the argument is `False`, only include tasks _without_ a project.
        If the argument is `True`, only include tasks _with_ a project.
        If the argument is `None` (default), then include all tasks.

    heading : str or None, optional
        Any valid uuid of a heading. Only include tasks matching that heading.
        If the argument is `False`, only include tasks _without_ a heading.
        If the argument is `True`, only include tasks _with_ a heading.
        If the argument is `None` (default), then include all tasks.

    tag : str or None, optional
        Any valid title of a tag. Only include tasks matching that tag.
        If the argument is `False`, only include tasks _without_ tags.
        If the argument is `True`, only include tasks _with_ tags.
        If the argument is `None` (default), then include all tasks.

    start_date : bool or None, optional
        If the argument is `False`, only include tasks _without_ a start date.
        If the argument is `True`, only include tasks _with_ a start date.
        If the argument is `None` (default), then include all tasks.

    deadline : bool or None, optional
        If the argument is `False`, only include tasks _without_ a deadline.
        If the argument is `True`, only include tasks _with_ a deadline.
        If the argument is `None` (default), then include all tasks.

    search_query : str, optional
        The string value is passed to the SQL LIKE operator. It can thus
        include placeholders such as '%' and '_'. Per default, it is
        wrapped in '% ... %'.

        Currently titles and notes of to-dos, projects, headings, and areas
        are taken into account.

        If the query is `False`, then return items where titles or notes
        are empty.

        If the query `None`, then return all items.

    index : {'index', 'todayIndex'}, default 'index'
        Database field to order result by.

    count_only : boolean, default False
        Only output length of result. This is done by a SQL COUNT query.

    filepath : str, optional
        Any valid path of a SQLite database file generated by the Things app.
        If the environment variable THINGSDB is set, then that path will be used.
        Otherwise, access the default database path.

    database : things.database.Database, optional
        Any valid `things.database.Database` object previously instantiated.

    Returns
    -------
    list of dict (default)
        Representing multiple tasks.
    dict (if `uuid` is given)
        Representing a single task.
    int (count_only == True)
        Count of matching Tasks.

    Examples
    --------
    >>> things.tasks()
    ...
    >>> things.tasks('2Ukg8I2nLukhyEM7wYiBeb')
    ...
    >>> things.tasks(area='hIo1FJlAYGKt1Yj38vzKc3', include_items=True)
    ...
    >>> things.tasks(status='completed', count_only=True)
    10

    """
    database = pop_database(kwargs)
    result = database.get_tasks(
        uuid=uuid, status=kwargs.pop("status", "incomplete"), **kwargs
    )

    if kwargs.get("count_only"):
        return result

    # overwrite `include_items` if fetching a single task.
    if uuid:
        include_items = True

    for task in result:
        # TK: How costly of an operation is it to do this for every task?
        # IF costly, then can it be made significantly more efficient
        # by optimizing SQL calls?

        if task.get("tags"):
            task["tags"] = database.get_tags(task=task["uuid"])

        if not include_items:
            continue

        # include items
        if task["type"] == "to-do":
            if task.get("checklist"):
                task["checklist"] = database.get_checklist_items(task_uuid=task["uuid"])
        elif task["type"] == "project":
            project = task
            project["items"] = items = tasks(
                project=project["uuid"],
                include_items=True,
                database=database,
            )
            # to-dos without headings appear before headings in app
            items.sort(key=lambda item: item["type"], reverse=True)
        elif task["type"] == "heading":
            heading = task
            heading["items"] = tasks(
                type="to-do",
                heading=heading["uuid"],
                include_items=True,
                database=database,
            )

    if uuid:
        result = result[0]

    return result


def areas(uuid=None, include_items=False, **kwargs):
    """
    Read areas into dicts.

    Parameters
    ----------
    uuid : str or None, optional
        Any valid uuid of an area. If None, then return all areas.

    include_items : boolean, default False
        Include tasks and projects in each area.

    tag : str or None, optional
        Any valid title of a tag. Only include areas matching that tag.
        If the argument is `False`, only include areas _without_ tags.
        If the argument is `True`, only include areas _with_ tags.
        If the argument is `None`, then ignore any tags present, that is,
        include areas both with and without tags.

    count_only : boolean, default False
        Only output length of result. This is done by a SQL COUNT query.

    filepath : str, optional
        Any valid path of a SQLite database file generated by the Things app.
        If no path is provided, then access the default database path.

    database : things.database.Database, optional
        Any valid `things.database.Database` object previously instantiated.

    Returns
    -------
    list of dict (default)
        Representing Things areas.
    dict (if `uuid` is given)
        Representing a single Things area.
    int (count_only == True)
        Count of matching areas.

    Examples
    --------
    >>> things.areas()
    ...
    >>> things.areas(tag='Home')
    ...
    >>> things.areas(uuid='Gw9QefIdgR6nPEoY5hBNSh')
    ...
    >>> things.areas(include_items=True, status='completed')
    ...
    """
    database = pop_database(kwargs)
    result = database.get_areas(uuid=uuid, **kwargs)

    if kwargs.get("count_only"):
        return result

    for area in result:
        if area.get("tags"):
            area["tags"] = database.get_tags(area=area["uuid"])
        if include_items:
            area["items"] = tasks(
                area=area["uuid"], include_items=True, database=database
            )

    if uuid:
        result = result[0]

    return result


def tags(title=None, include_items=False, **kwargs):
    """
    Read tags into dicts.

    Parameters
    ----------
    title : str, optional
        Any valid title of a tag. Include all items of said tag.
        If None, then return all tags.

    include_items : boolean, default False
        For each tag, include items tagged with that tag.
        Items may include areas, tasks, and projects.

    area : str, optional
        Valid uuid of an area. Return tags of said area.

    task : str, optional
        Valid uuid of a task. Return tags of said task.

    titles_only : bool, default False
        If True, only return list of titles of tags.

    filepath : str, optional
        Any valid path of a SQLite database file generated by the Things app.
        If no path is provided, then access the default database path.

    database : things.database.Database, optional
        Any valid `things.database.Database` object previously instantiated.

    Returns
    -------
    list of dict (default)
        Representing tags.
    list of str (if `titles_only == True` or area / task is given)
        Representing tag titles.
    dict (if `title` is given)
        Representing a single Things tag.

    Examples
    --------
    >>> things.tags()
    ...
    >>> things.tags('Home')
    ...
    >>> things.tags(include_items=True)
    ...
    >>> things.tags(task='2Ukg8I2nLukhyEM7wYiBeb')
    ...
    """
    database = pop_database(kwargs)
    result = database.get_tags(title=title, **kwargs)

    if include_items:
        for tag in result:
            tag_title = tag["title"]
            tag["items"] = [
                *areas(tag=tag_title, database=database),
                *tasks(tag=tag_title, database=database),
            ]

    if title:
        result = result[0]

    return result


# --------------------------------------------------
# Utility API functions derived from above
# --------------------------------------------------


def search(query: str, **kwargs) -> List[Dict]:
    """
    Search tasks in the database.

    Currently any part of a title and note of a to-do, project,
    heading, or area is matched.

    See the `search_query` parameter of `things.api.tasks` for details.

    Examples
    --------
    >>> things.search('book')
    [{'uuid': 'YrOmUnEXASmpq8ch6RsyPt',
      'type': 'to-do',
      'title': 'Book a hotel room',
      ...},
      {'uuid': 'KVHAxIIJ52a0h1RCbmg5D6',
      'type': 'to-do',
      'title': 'Book flights',
      ...}]

    >>> things.search('book%room')
    [{'uuid': 'YrOmUnEXASmpq8ch6RsyPt',
      'type': 'to-do',
      'title': 'Book a hotel room',
      ...}]
    """
    return tasks(search_query=query, **kwargs)


def get(uuid, default=None, **kwargs):
    """
    Find an object by uuid. If not found, return `default`.

    Currently supports tasks, projects, headings, areas, and tags.
    """
    try:
        return tasks(uuid=uuid, **kwargs)
    except ValueError:
        pass

    try:
        return areas(uuid=uuid, **kwargs)
    except ValueError:
        pass

    for tag in tags(**kwargs):
        if tag["uuid"] == uuid:
            return tag

    return default


# Filter by object type


def todos(uuid=None, **kwargs):
    """
    Read to-dos into dicts.

    See `things.api.tasks` for details.
    """
    return tasks(uuid=uuid, type="to-do", **kwargs)


def projects(uuid=None, **kwargs):
    """
    Read projects into dicts.

    See `things.api.tasks` for details.
    """
    return tasks(uuid=uuid, type="project", **kwargs)


def checklist_items(uuid, **kwargs):
    """
    Read checklist items into dicts.
    See `things.api.tasks` for details.

    Returns
    -------
    list of dict
        Representing checklist items. Or [] if none found.
    """
    return tasks(uuid=uuid, type="to-do", **kwargs).get("checklist", [])


# Filter by collections in the Things app sidebar.


def inbox(**kwargs):
    """
    Read inbox into dicts.

    See `things.api.tasks` for details.
    """
    return tasks(start="Inbox", **kwargs)


def today(**kwargs):
    """
    Note: This might not produce desired results if the Things app hasn't
    been opened yet today and the yellow "OK" button clicked for new tasks.
    In general, you can assume that whatever state the Things app was in
    when you last opened it, that's the state reflected here by the API.
    """
    database = pop_database(kwargs)
    if not database.was_modified_today():
        print(
            "[NOTE] The results reflect the state of the Things app "
            "when it was last run. If the results seem out of date, "
            "then run the Things app and click the yellow 'OK' button "
            "to update Today's to-dos and projects.",
            file=sys.stderr,
        )
    return tasks(
        start_date=True,
        start="Anytime",
        index="todayIndex",
        database=database,
        **kwargs,
    )


def upcoming(**kwargs):
    """
    Note: unscheduled tasks with a deadline are not included here.
    See the `deadline` function instead.
    """
    return tasks(start_date=True, start="Someday", **kwargs)


def anytime(**kwargs):
    """
    Read anytime tasks into dicts.

    See `things.api.tasks` for details.
    """
    return tasks(start="Anytime", **kwargs)


def someday(**kwargs):
    """
    Read someday tasks into dicts.

    See `things.api.tasks` for details.
    """
    return tasks(start_date=False, start="Someday", **kwargs)


def logbook(**kwargs):
    """
    Read logbook tasks into dicts.

    See `things.api.tasks` for details.
    """
    result = [*canceled(**kwargs), *completed(**kwargs)]
    result.sort(key=lambda task: task["stop_date"], reverse=True)
    return result


def trash(**kwargs):
    """
    Read trashed tasks into dicts.

    See `things.api.tasks` for details.
    """
    result = [*canceled(**kwargs), *completed(**kwargs)]
    result.sort(key=lambda task: task["stop_date"], reverse=True)
    return result


# Filter by various task properties


def canceled(**kwargs):
    """
    Read canceled tasks into dicts.

    See `things.api.tasks` for details.
    """
    return tasks(status="canceled", **kwargs)


def completed(**kwargs):
    """
    Examples
    --------
    >>> things.completed(count_only=True)
    14
    >>> things.completed(type='project', count_only=True)
    4
    """
    return tasks(status="completed", **kwargs)


def deadlines(**kwargs):
    """
    Read tasks with deadlines into dicts.

    See `things.api.tasks` for details.
    """
    result = tasks(deadline=True, **kwargs)
    result.sort(key=lambda task: task["deadline"])
    return result


# Interact with Things app


def link(uuid):
    """
    Returns a things:///show?id=uuid link.
    """

    return f"things:///show?id={uuid}"


def show(uuid):
    """
    Show a certain uuid in the Things app.

    Parameters
    ----------
    uuid : str
        A valid uuid of any Things object.

    Examples
    --------
    >>> tag = things.tags('Home')
    >>> things.show(tag['uuid'])
    """
    uri = link(uuid)
    os.system(f"open {quote(uri)}")


# Helper functions


def pop_database(kwargs):
    """instantiate non-default database from `kwargs` if provided"""
    filepath, database = kwargs.pop("filepath", None), kwargs.pop("database", None)
    if not database:
        database = Database(filepath=filepath)
    return database
