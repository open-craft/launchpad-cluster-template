import os
import secrets

from jinja2.ext import Extension


class EnvVarExtension(Extension):
    """
    Provides access to environment variables in templates.
    """

    def __init__(self, environment):
        super(EnvVarExtension, self).__init__(environment)
        environment.globals["env"] = os.getenv


class PasswordExtension(Extension):
    """
    Provides password generation in templates.
    """

    def __init__(self, environment):
        super(PasswordExtension, self).__init__(environment)
        environment.globals["generate_password"] = lambda: secrets.token_hex(24)


class StorageExtension(Extension):
    """
    Provides storage-related utilities for seeding tutor-contrib-s3 settings.
    """

    def __init__(self, environment):
        super(StorageExtension, self).__init__(environment)
        environment.globals["s3_host"] = self.__get_s3_host

    def __get_s3_host(self, storage_type, region):
        """
        Return the S3_HOST value for tutor-contrib-s3.

        AWS uses an empty host (default endpoints). DigitalOcean Spaces uses
        ``{region}.digitaloceanspaces.com``.
        """

        storage_type = (storage_type or "spaces").lower()
        region = region or "nyc3"

        if storage_type == "spaces":
            return f"{region}.digitaloceanspaces.com"

        if storage_type == "s3":
            return ""

        raise ValueError(f"Unknown storage type: {storage_type}")
