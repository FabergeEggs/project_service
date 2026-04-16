class ProjectNotFoundError(Exception):
    ...


class ProjectAlreadyExistsError(Exception):
    ...


class ProjectPostNotFoundError(Exception):
    ...


class ProjectPostAlreadyExistsError(Exception):
    ...


class ProjectTaskNotFoundError(Exception):
    ...


class ProjectTaskAlreadyExistsError(Exception):
    ...


class ProjectUserErorr(Exception):
    ...


class ProjectUserNotFoundError(ProjectUserErorr):
    ...


class ProjectUserAlreadyExistsError(ProjectUserErorr):
    ...
