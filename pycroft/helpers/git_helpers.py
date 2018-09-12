from datetime import datetime
from logging import getLogger
from subprocess import call

import git
from flask_babel import format_datetime
from git.exc import (GitCommandError, InvalidGitRepositoryError,
                     NoSuchPathError, CacheError)

logger = getLogger(__name__)


def init_repo(repo_dir, repo_url):
    """Initialize a new git repository in `git_dir` from `repo_url`"""
    try:
        repo = git.Repo(repo_dir)
    except (NoSuchPathError, InvalidGitRepositoryError):
        call(["git", "clone", repo_url, repo_dir, "-q"])
        repo = git.Repo(repo_dir)

    if repo.remotes:
        origin = repo.remote('origin')
    else:
        origin = repo.create_remote('origin', repo_url)

    try:
        origin.fetch()
    except GitCommandError:
        logger.error("Git fetch failed", extra={'data': {'repo_dir': repo_dir}})
        return

    try:
        master = repo.refs['master']
    except IndexError:
        raise OSError("Git directory {} doesn't have a master!".format(repo_dir))

    repo.head.set_reference(master)

    repo.git.reset('--hard', 'origin/master')
    logger.info("Initialized git repository %s in %s", repo_url, repo_dir)


def update_repo(repo_dir):
    repo = git.Repo.init(repo_dir)

    try:
        if repo.commit().hexsha != repo.remote().fetch()[0].commit.hexsha:
            origin = repo.remote()
            origin.fetch()
            repo.git.reset('--hard', 'origin/master')
            return True
        else:
            return False
    except GitCommandError:
        logger.error("Git fetch failed", extra={'data': {'repo_dir': repo_dir}})
    else:
        logger.info("Fetched git repository", extra={'data': {
            'repo_dir': repo_dir
        }})


def get_repo_active_branch(repo_dir):
    """
    :param repo_dir: path of repo
    :type repo_dir: str
    :return: name of currently checked out branch
    :rtype: str
    """
    try:
        pycroft_repo = git.Repo(repo_dir)
        return pycroft_repo.active_branch.name
    except GitCommandError:
        return "Unknown"
    except TypeError:  # detatched HEAD
        return "@{}".format(pycroft_repo.head.commit.hexsha[:8])


def get_latest_commits(repo_dir, commit_count):
    """
    :param repo_dir: path of repo
    :type repo_dir: str
    :param commit_count: number of commits to return
    :type commit_count: int
    :return: commit information (hash, message, author, date) about
    commit_count last commits
    :rtype: list of dicts
    """
    try:
        pycroft_repo = git.Repo(repo_dir)
        commits = pycroft_repo.iter_commits(max_count=commit_count)
        return [{
            'hexsha': commit.hexsha,
            'message': commit.summary,
            'author': commit.author,
            'date': format_datetime(datetime.fromtimestamp(
                commit.committed_date)),
        } for commit in commits]
    except (InvalidGitRepositoryError, CacheError, GitCommandError):
        logger.exception("Could not get latest commits", extra={'data': {
            'repo_dir': repo_dir}})
        return []
