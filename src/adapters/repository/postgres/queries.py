class TagQueries:
    UPSERT_TAG = """
        INSERT INTO tags (id, name, count)
        VALUES (%s, %s, %s)
        ON CONFLICT (name) DO UPDATE SET
            count = tags.count + 1
        """

    SELECT_TAG_ID_BY_NAME = """
        SELECT id FROM tags WHERE name = %s
        """


class ProjectQueries:
    INSERT_PROJECT = """
        INSERT INTO project (
            id, label, short_description, description,
            creator_id, status, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

    SELECT_PROJECT_INFO = """
        SELECT p.id, p.label, p.short_description, p.description, p.creator_id,
            du.name AS creator, p.status, p.created_at
        FROM project p
        LEFT JOIN denorm_user du ON du.id = p.creator_id
        WHERE p.id = %s AND p.status != 'DELETED'
        """

    SELECT_PROJECT_TAGS = """
        SELECT t.id, t.name, t.count
        FROM tags t
        JOIN project_tag_connection ptc ON ptc.tag_id = t.id
        WHERE ptc.project_id = %s
        """

    SELECT_PROJECT_STATISTICS = """
        SELECT
            (SELECT COUNT(puc.user_id)
             FROM project_user_connection puc
             WHERE puc.project_id = p.id) as members_count,
            (SELECT COUNT(t.id)
             FROM task t
             WHERE t.project_id = p.id
               AND t.status != 'DELETED') as tasks_count,
            (SELECT COALESCE(SUM(t.answer_count), 0)
             FROM task t
             WHERE t.project_id = p.id
               AND t.status != 'DELETED') as total_answers_count
        FROM project p
        WHERE p.id = %s
            AND p.status != 'DELETED'
        """

    UPDATE_PROJECT = """
        UPDATE project
        SET label = %s,
            short_description = %s,
            description = %s,
            updated_at = %s,
            status = %s
        WHERE id = %s
        RETURNING id
        """

    SELECT_PROJECTS_BY_IDS = """
        SELECT p.id, p.label, p.short_description, p.description,
        p.creator_id, du.name AS creator, p.status, p.created_at, p.updated_at
        FROM project p
        LEFT JOIN denorm_user du ON du.id = p.creator_id
        WHERE p.id = ANY(%s) AND p.status != 'DELETED'
        """

    SELECT_PROJECT_PUBLICATIONS = """
        (
            SELECT
                p.id as id,
                p.project_id,
                p.label,
                p.short_description,
                p.created_at,
                p.creator_id,
                du.name as creator_name,
                'post' as type,
                NULL as status,
                p.comments_count as answers_count,
                p.media_ids as media_ids
            FROM post p
            LEFT JOIN denorm_user du ON du.id = p.creator_id
            WHERE p.project_id = %s
                AND (%s::timestamptz IS NULL OR p.created_at < %s)
        )
        UNION ALL
        (
            SELECT
                t.id as id,
                t.project_id,
                t.label,
                t.short_description,
                t.created_at,
                t.creator_id,
                du.name as creator_name,
                'task' as type,
                t.status as status,
                t.answer_count as answers_count,
                t.media_ids as media_ids
            FROM task t
            LEFT JOIN denorm_user du ON du.id = t.creator_id
            WHERE t.project_id = %s
                AND (%s::timestamptz IS NULL OR t.created_at < %s)
        )
        ORDER BY created_at DESC
        LIMIT %s
        """

    INSERT_PROJECT_TAG_CONNECTION = """
        INSERT INTO project_tag_connection (project_id, tag_id)
        VALUES (%s, %s)
        ON CONFLICT (project_id, tag_id) DO NOTHING
        """

    INSERT_PROJECT_TAG_CONNECTION_NO_CONFLICT = """
        INSERT INTO project_tag_connection (project_id, tag_id)
        VALUES (%s, %s)
        """

    DELETE_PROJECT_TAG_CONNECTIONS = """
        DELETE FROM project_tag_connection WHERE project_id = %s
        """


class TaskQueries:
    INSERT_TASK = """
        INSERT INTO task (
            id, project_id, label, creator_id,
            short_description, description,
            created_at, updated_at,
            answer_count, status, media_ids
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    UPDATE_TASK = """
        UPDATE task
        SET project_id = %s, label = %s, creator_id = %s,
            short_description = %s, description = %s,
            updated_at = %s, status = %s
        WHERE id = %s
        RETURNING id
        """

    SELECT_TASK = """
        SELECT t.id, t.project_id, t.label, t.short_description,
            t.description, t.creator_id, du.name AS creator,
            t.status, t.created_at, t.updated_at, t.answer_count,
            t.media_ids
        FROM task t
        LEFT JOIN denorm_user du ON du.id = t.creator_id
        WHERE t.id = %s AND t.status != 'DELETED'
        """

    INCREMENT_TASK_ANSWER = """
        UPDATE task
        SET answer_count = answer_count + 1,
            updated_at = NOW()
        WHERE id = %s AND status != 'DELETED'
        RETURNING id
        """

    DECREMENT_TASK_ANSWER = """
        UPDATE task
        SET answer_count = answer_count - 1,
            updated_at = NOW()
        WHERE id = %s AND status != 'DELETED' AND answer_count > 0
        RETURNING id
        """


class PostQueries:
    INSERT_POST = """
        INSERT INTO post (
            id, project_id, label, creator_id,
            short_description, description,
            comments_count, created_at, updated_at, media_ids
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

    UPDATE_POST = """
        UPDATE post
        SET project_id = %s, label = %s, creator_id = %s,
            short_description = %s, description = %s,
            updated_at = %s
        WHERE id = %s
        RETURNING id
        """

    DELETE_POST = """
        DELETE FROM post
        WHERE id = %s
        RETURNING id
        """

    SELECT_POST = """
        SELECT t.id, t.project_id, t.label, t.creator_id,
        du.name AS creator_name, t.short_description, t.description,
        t.comments_count, t.created_at, t.updated_at, t.media_ids
        FROM post t
        LEFT JOIN denorm_user du ON du.id = t.creator_id
        WHERE t.id = %s
        """

    INCREMENT_POST_ANSWER = """
        UPDATE post
        SET comments_count = comments_count + 1,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id
        """

    DECREMENT_POST_ANSWER = """
        UPDATE post
        SET comments_count = comments_count - 1,
            updated_at = NOW()
        WHERE id = %s AND comments_count > 0
        RETURNING id
        """


class MembershipQueries:
    SELECT_USER_MEMBERSHIPS = """
        SELECT
        p.id,
        p.label,
        p.short_description,
        p.status,
        p.created_at,
        puc.role,
        u.name as creator_name
        FROM project_user_connection puc
        JOIN project p ON p.id=puc.project_id
        LEFT JOIN denorm_user u ON u.id=p.creator_id
        WHERE puc.user_id= %s
        AND p.status != 'DELETED'
        AND puc.role != 'DELETED'
        """

    INSERT_MEMBERSHIP = """
        INSERT INTO project_user_connection (project_id, user_id, role)
        VALUES (%s, %s, %s)
        ON CONFLICT (project_id, user_id) DO NOTHING
    """

    UPSERT_MEMBER = """
        INSERT INTO project_user_connection (project_id, user_id, role)
        VALUES (%s, %s, %s)
        ON CONFLICT (project_id, user_id) DO UPDATE
        SET role = EXCLUDED.role
        """

    DELETE_MEMBER = """
        DELETE FROM project_user_connection
        WHERE project_id = %s AND user_id = %s
        RETURNING project_id, user_id
        """
