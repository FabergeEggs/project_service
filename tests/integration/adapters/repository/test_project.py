import uuid
from datetime import datetime, timezone

import pytest

from src.models.project import (
    Project, Task, Post, Tag, DenormUser,
    ProjectStatusEnum, TaskStatusEnum, ProjectRoleEnum,
)
import src.adapters.repository.errors as adapter_errors


def make_project(creator_id: uuid.UUID, **kwargs) -> Project:
    defaults = dict(
        id=uuid.uuid4(),
        label="Test Project",
        short_description="Short desc",
        description="Full description",
        creator_id=creator_id,
        status=ProjectStatusEnum.ACTIVE,
        tags=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Project(**defaults)


def make_task(project_id: uuid.UUID, creator_id: uuid.UUID, **kwargs) -> Task:
    defaults = dict(
        task_id=uuid.uuid4(),
        project_id=project_id,
        creator_id=creator_id,
        label="Test Task",
        short_description="Short desc",
        description="Full description",
        status=TaskStatusEnum.ACTIVE,
        answers_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Task(**defaults)


def make_post(project_id: uuid.UUID, creator_id: uuid.UUID, **kwargs) -> Post:
    defaults = dict(
        post_id=uuid.uuid4(),
        project_id=project_id,
        creator_id=creator_id,
        label="Test Post",
        short_description="Short desc",
        description="Full description",
        comments_count=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Post(**defaults)


@pytest.mark.integration
class TestCreateProject:
    @pytest.mark.asyncio
    async def test_creates_and_returns_uuid(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        assert isinstance(project_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_project_can_be_retrieved_after_creation(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id, label="Unique Project")
        project_id = await project_repository.create_project(project)

        result = await project_repository.get_project_info(project_id)

        assert result["id"] == project_id
        assert result["label"] == "Unique Project"
        assert result["creator_id"] == creator_id
        assert result["status"] == ProjectStatusEnum.ACTIVE

    @pytest.mark.asyncio
    async def test_creates_project_with_tags(self, project_repository, creator_id):
        tags = [Tag(tag_id=None, name="python"),
                Tag(tag_id=None, name="fastapi")]
        project = make_project(creator_id=creator_id, tags=tags)
        project_id = await project_repository.create_project(project)

        result = await project_repository.get_project_info(project_id)

        tag_names = {t.name for t in result["tags"]}
        assert "python" in tag_names
        assert "fastapi" in tag_names

    @pytest.mark.asyncio
    async def test_raises_on_duplicate_id(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        await project_repository.create_project(project)

        with pytest.raises(adapter_errors.ProjectAlreadyExistsError):
            await project_repository.create_project(project)


@pytest.mark.integration
class TestGetProjectInfo:
    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.ProjectNotFoundError):
            await project_repository.get_project_info(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_returns_correct_fields(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id,
                               description="Detailed description")
        project_id = await project_repository.create_project(project)

        result = await project_repository.get_project_info(project_id)

        assert result["description"] == "Detailed description"
        assert "creator_name" in result
        assert "tags" in result
        assert isinstance(result["tags"], list)


@pytest.mark.integration
class TestUpdateProject:
    @pytest.mark.asyncio
    async def test_updates_label_and_status(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        project.id = project_id
        project.label = "Updated Label"
        project.status = ProjectStatusEnum.FINISHED
        await project_repository.update_project(project)

        result = await project_repository.get_project_info(project_id)
        assert result["label"] == "Updated Label"
        assert result["status"] == ProjectStatusEnum.FINISHED

    @pytest.mark.asyncio
    async def test_updates_tags(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id, tags=[
                               Tag(tag_id=None, name="old-tag")])
        project_id = await project_repository.create_project(project)

        project.id = project_id
        project.tags = [Tag(tag_id=None, name="new-tag")]
        await project_repository.update_project(project)

        result = await project_repository.get_project_info(project_id)
        tag_names = {t.name for t in result["tags"]}
        assert "new-tag" in tag_names
        assert "old-tag" not in tag_names

    @pytest.mark.asyncio
    async def test_raises_when_project_not_found(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id, id=uuid.uuid4())
        with pytest.raises(adapter_errors.ProjectNotFoundError):
            await project_repository.update_project(project)


@pytest.mark.integration
class TestGetProjects:
    @pytest.mark.asyncio
    async def test_returns_multiple_projects(self, project_repository, creator_id):
        p1 = make_project(creator_id=creator_id, label="Project 1")
        p2 = make_project(creator_id=creator_id, label="Project 2")
        id1 = await project_repository.create_project(p1)
        id2 = await project_repository.create_project(p2)

        results = await project_repository.get_projects([id1, id2])

        assert len(results) == 2
        labels = {r["label"] for r in results}
        assert "Project 1" in labels
        assert "Project 2" in labels

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_unknown_ids(self, project_repository):
        results = await project_repository.get_projects([uuid.uuid4()])
        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self, project_repository):
        results = await project_repository.get_projects([])
        assert results == []


@pytest.mark.integration
class TestGetProjectStatistics:
    @pytest.mark.asyncio
    async def test_returns_zeros_for_empty_project(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        stats = await project_repository.get_project_statistics(project_id)

        assert stats["tasks_count"] == 0
        assert stats["members_count"] == 0
        assert stats["answers_count"] == 0

    @pytest.mark.asyncio
    async def test_counts_tasks(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id, creator_id=creator_id)
        await project_repository.create_task(task)

        stats = await project_repository.get_project_statistics(project_id)
        assert stats["tasks_count"] == 1

    @pytest.mark.asyncio
    async def test_raises_when_project_not_found(self, project_repository):
        with pytest.raises(adapter_errors.ProjectNotFoundError):
            await project_repository.get_project_statistics(uuid.uuid4())


@pytest.mark.integration
class TestCreateTask:
    @pytest.mark.asyncio
    async def test_creates_and_returns_uuid(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id, creator_id=creator_id)
        task_id = await project_repository.create_task(task)

        assert isinstance(task_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_task_can_be_retrieved(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id,
                         creator_id=creator_id, label="My Task")
        task_id = await project_repository.create_task(task)

        result = await project_repository.get_task(task_id)

        assert result["task_id"] == task_id
        assert result["label"] == "My Task"
        assert result["project_id"] == project_id
        assert result["creator_id"] == creator_id
        assert result["status"] == TaskStatusEnum.ACTIVE
        assert result["answers_count"] == 0

    @pytest.mark.asyncio
    async def test_raises_on_duplicate_id(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id, creator_id=creator_id)
        await project_repository.create_task(task)

        with pytest.raises(adapter_errors.TaskAlreadyExistsError):
            await project_repository.create_task(task)


@pytest.mark.integration
class TestGetTask:
    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.TaskNotFoundError):
            await project_repository.get_task(uuid.uuid4())


@pytest.mark.integration
class TestUpdateTask:
    @pytest.mark.asyncio
    async def test_updates_label_and_status(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id, creator_id=creator_id)
        task_id = await project_repository.create_task(task)

        task.task_id = task_id
        task.label = "Updated Task"
        task.status = TaskStatusEnum.FINISHED
        await project_repository.update_task(task)

        result = await project_repository.get_task(task_id)
        assert result["label"] == "Updated Task"
        assert result["status"] == TaskStatusEnum.FINISHED

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id,
                         creator_id=creator_id, task_id=uuid.uuid4())
        with pytest.raises(adapter_errors.TaskNotFoundError):
            await project_repository.update_task(task)


@pytest.mark.integration
class TestTaskAnswerCounters:
    @pytest.mark.asyncio
    async def test_increment_task_answer(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        task = make_task(project_id=project_id, creator_id=creator_id)
        task_id = await project_repository.create_task(task)

        await project_repository.increment_task_answer(task_id)

        result = await project_repository.get_task(task_id)
        assert result["answers_count"] == 1

    @pytest.mark.asyncio
    async def test_decrement_task_answer(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        task = make_task(project_id=project_id,
                         creator_id=creator_id, answers_count=2)
        task_id = await project_repository.create_task(task)

        await project_repository.decrement_task_answer(task_id)

        result = await project_repository.get_task(task_id)
        assert result["answers_count"] == 1

    @pytest.mark.asyncio
    async def test_increment_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.TaskNotFoundError):
            await project_repository.increment_task_answer(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_decrement_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.TaskNotFoundError):
            await project_repository.decrement_task_answer(uuid.uuid4())


@pytest.mark.integration
class TestCreatePost:
    @pytest.mark.asyncio
    async def test_creates_and_returns_uuid(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        post = make_post(project_id=project_id, creator_id=creator_id)
        post_id = await project_repository.create_post(post)

        assert isinstance(post_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_post_can_be_retrieved(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        post = make_post(project_id=project_id,
                         creator_id=creator_id, label="My Post")
        post_id = await project_repository.create_post(post)

        result = await project_repository.get_post(post_id)

        assert result["post_id"] == post_id
        assert result["label"] == "My Post"
        assert result["project_id"] == project_id
        assert result["creator_id"] == creator_id
        assert result["comments_count"] == 0

    @pytest.mark.asyncio
    async def test_raises_on_duplicate_id(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        post = make_post(project_id=project_id, creator_id=creator_id)
        await project_repository.create_post(post)

        with pytest.raises(adapter_errors.PostAlreadyExistsError):
            await project_repository.create_post(post)


@pytest.mark.integration
class TestGetPost:
    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.PostNotFoundError):
            await project_repository.get_post(uuid.uuid4())


@pytest.mark.integration
class TestUpdatePost:
    @pytest.mark.asyncio
    async def test_updates_label(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        post = make_post(project_id=project_id, creator_id=creator_id)
        post_id = await project_repository.create_post(post)

        post.post_id = post_id
        post.label = "Updated Post"
        await project_repository.update_post(post)

        result = await project_repository.get_post(post_id)
        assert result["label"] == "Updated Post"

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        post = make_post(project_id=project_id,
                         creator_id=creator_id, post_id=uuid.uuid4())
        with pytest.raises(adapter_errors.PostNotFoundError):
            await project_repository.update_post(post)


@pytest.mark.integration
class TestDeletePost:
    @pytest.mark.asyncio
    async def test_deletes_post(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        post = make_post(project_id=project_id, creator_id=creator_id)
        post_id = await project_repository.create_post(post)

        await project_repository.delete_post(post_id)

        with pytest.raises(adapter_errors.PostNotFoundError):
            await project_repository.get_post(post_id)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.PostNotFoundError):
            await project_repository.delete_post(uuid.uuid4())


@pytest.mark.integration
class TestPostAnswerCounters:
    @pytest.mark.asyncio
    async def test_increment_post_answer(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        post = make_post(project_id=project_id, creator_id=creator_id)
        post_id = await project_repository.create_post(post)

        await project_repository.increment_post_answer(post_id)

        result = await project_repository.get_post(post_id)
        assert result["comments_count"] == 1

    @pytest.mark.asyncio
    async def test_decrement_post_answer(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        post = make_post(project_id=project_id,
                         creator_id=creator_id, comments_count=2)
        post_id = await project_repository.create_post(post)

        await project_repository.decrement_post_answer(post_id)

        result = await project_repository.get_post(post_id)
        assert result["comments_count"] == 1

    @pytest.mark.asyncio
    async def test_increment_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.PostNotFoundError):
            await project_repository.increment_post_answer(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_decrement_raises_when_not_found(self, project_repository):
        with pytest.raises(adapter_errors.PostNotFoundError):
            await project_repository.decrement_post_answer(uuid.uuid4())


@pytest.mark.integration
class TestAddMember:
    @pytest.mark.asyncio
    async def test_adds_member_to_project(self, project_repository, creator_id, member_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        user = DenormUser(
            id=member_id,
            name="Test Member",
            role=ProjectRoleEnum.VOLUNTEER,
            avatar_link="http://example.com/avatar.png",
        )
        await project_repository.add_member(project_id, user)

        stats = await project_repository.get_project_statistics(project_id)
        assert stats["members_count"] == 1

    @pytest.mark.asyncio
    async def test_upserts_on_duplicate_member(self, project_repository, creator_id, member_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        user = DenormUser(
            id=member_id,
            name="Test Member",
            role=ProjectRoleEnum.VOLUNTEER,
            avatar_link="http://example.com/avatar.png",
        )
        await project_repository.add_member(project_id, user)
        await project_repository.add_member(project_id, user)

        stats = await project_repository.get_project_statistics(project_id)
        assert stats["members_count"] == 1


@pytest.mark.integration
class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_removes_member(self, project_repository, creator_id, member_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)
        user = DenormUser(
            id=member_id,
            name="Test Member",
            role=ProjectRoleEnum.VOLUNTEER,
            avatar_link="http://example.com/avatar.png",
        )

        await project_repository.add_member(project_id, user)
        await project_repository.remove_member(project_id, user.id)

        stats = await project_repository.get_project_statistics(project_id)
        assert stats["members_count"] == 0

    @pytest.mark.asyncio
    async def test_raises_when_user_not_member(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        with pytest.raises(adapter_errors.UserNotFoundError):
            await project_repository.remove_member(project_id, uuid.uuid4())


@pytest.mark.integration
class TestGetUserMemberships:
    @pytest.mark.asyncio
    async def test_returns_memberships_by_role(self, project_repository, creator_id, member_id, member_id_2):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        scientist = DenormUser(
            id=member_id,
            name="Test Member",
            role=ProjectRoleEnum.SCIENTIST,
            avatar_link="http://example.com/avatar.png",
        )
        volunteer = DenormUser(
            id=member_id_2,
            name="Test Member 2",
            role=ProjectRoleEnum.VOLUNTEER,
            avatar_link="http://example.com/avatar.png",
        )

        await project_repository.add_member(project_id, scientist)
        await project_repository.add_member(project_id, volunteer)

        scientist_list, _ = await project_repository.get_user_memberships(member_id)
        _, volunteer_list = await project_repository.get_user_memberships(member_id_2)

        assert len(scientist_list) == 1
        assert len(volunteer_list) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_user(self, project_repository):
        scientists, volunteers = await project_repository.get_user_memberships(uuid.uuid4())
        assert scientists == []
        assert volunteers == []


@pytest.mark.integration
class TestUpsertDenormUser:
    @pytest.mark.asyncio
    async def test_inserts_new_user(self, project_repository):
        user_id = uuid.uuid4()
        await project_repository.upsert_denorm_user(
            user_id, {"name": "Alice", "avatar_url": "http://x.com/a.png"}
        )

    @pytest.mark.asyncio
    async def test_updates_existing_user(self, project_repository):
        user_id = uuid.uuid4()
        await project_repository.upsert_denorm_user(
            user_id, {"name": "Bob", "avatar_url": "http://x.com/b.png"}
        )
        await project_repository.upsert_denorm_user(user_id, {"name": "Bobby"})

    @pytest.mark.asyncio
    async def test_raises_on_unknown_column(self, project_repository):
        with pytest.raises(ValueError):
            await project_repository.upsert_denorm_user(
                uuid.uuid4(), {"unknown_field": "value"}
            )


@pytest.mark.integration
class TestGetProjectPublications:
    @pytest.mark.asyncio
    async def test_returns_tasks_and_posts(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id, creator_id=creator_id)
        post = make_post(project_id=project_id, creator_id=creator_id)
        await project_repository.create_task(task)
        await project_repository.create_post(post)

        publications = await project_repository.get_project_publications(project_id, limit=20)

        assert len(publications) == 2
        types = {p["type"] for p in publications}
        assert "task" in types
        assert "post" in types

    @pytest.mark.asyncio
    async def test_respects_limit(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        for _ in range(5):
            task = make_task(project_id=project_id, creator_id=creator_id)
            await project_repository.create_task(task)

        publications = await project_repository.get_project_publications(project_id, limit=3)
        assert len(publications) == 3

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_project(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        publications = await project_repository.get_project_publications(project_id, limit=20)
        assert publications == []

    @pytest.mark.asyncio
    async def test_each_publication_has_required_fields(self, project_repository, creator_id):
        project = make_project(creator_id=creator_id)
        project_id = await project_repository.create_project(project)

        task = make_task(project_id=project_id, creator_id=creator_id)
        await project_repository.create_task(task)

        publications = await project_repository.get_project_publications(project_id, limit=20)
        pub = publications[0]

        for field in ("id", "project_id", "label", "short_description",
                      "created_at", "creator_id", "type", "answers_count"):
            assert field in pub
