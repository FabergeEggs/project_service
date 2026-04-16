class ProjectNotFoundError(Exception):
    ...


class ProjectAlreadyExistsError(Exception):
    ...


class PostNotFoundError(Exception):
    ...


class PostAlreadyExistsError(Exception):
    ...


class TaskNotFoundError(Exception):
    ...


class TaskAlreadyExistsError(Exception):
    ...


class UserErorr(Exception):
    ...


class UserNotFoundError(UserErorr):
    ...


class UserAlreadyExistsError(UserErorr):
    ...
