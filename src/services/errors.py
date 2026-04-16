class ProjectError(Exception):
    ...


class PostError(Exception):
    ...


class TaskError(Exception):
    ...


class ProjectNotFoundError(ProjectError):
    ...


class ProjectAlreadyExistsError(ProjectError):
    ...


class PostNotFoundError(PostError):
    ...


class PostAlreadyExistsError(PostError):
    ...


class TaskNotFoundError(TaskError):
    ...


class TaskAlreadyExistsError(TaskError):
    ...


class UserErorr(Exception):
    ...


class UserNotFoundError(UserErorr):
    ...


class UserAlreadyExistsError(UserErorr):
    ...
