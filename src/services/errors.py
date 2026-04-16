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


class ProjectPostNotFoundError(PostError):
    ...


class ProjectPostAlreadyExistsError(PostError):
    ...


class ProjectTaskNotFoundError(TaskError):
    ...


class ProjectTaskAlreadyExistsError(TaskError):
    ...


class ProjectUserErorr(Exception):
    ...


class ProjectUserNotFoundError(ProjectUserErorr):
    ...


class ProjectUserAlreadyExistsError(ProjectUserErorr):
    ...
