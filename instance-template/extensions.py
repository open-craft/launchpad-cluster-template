import os
import secrets

from jinja2.ext import Extension


def env(name, default=""):
    """
    Return an environment variable, treating a blank value as unset.

    GitHub Actions exports empty secrets as empty strings. ``os.getenv`` then
    returns that empty string instead of the default.
    """

    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return value


def mongodb_port(host, explicit_port=""):
    """
    Return the MongoDB port Tutor should write into Python settings.

    Tutor emits ``"port": {{ MONGODB_PORT }}`` without quotes, so the value
    must be a Python expression. Atlas SRV URIs cannot also carry a numeric
    port, so that case renders as ``None``.
    """

    port = str(explicit_port or "").strip()
    if port:
        return port
    if str(host or "").startswith("mongodb+srv://"):
        return "None"
    return "27017"


class EnvVarExtension(Extension):
    """
    Provides access to environment variables in templates.
    """

    def __init__(self, environment):
        super(EnvVarExtension, self).__init__(environment)
        environment.globals["env"] = env
        environment.globals["mongodb_port"] = mongodb_port


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

    def __get_s3_host(self, storage_type, region, host=""):
        """
        Return the S3_HOST value for tutor-contrib-s3.

        An explicit host, such as an UpCloud Managed Object Storage hostname,
        is returned unchanged. AWS uses an empty host (default endpoints).
        DigitalOcean Spaces uses ``{region}.digitaloceanspaces.com``.
        """

        if host:
            return host

        storage_type = (storage_type or "spaces").lower()
        region = region or "nyc3"

        if storage_type == "spaces":
            return f"{region}.digitaloceanspaces.com"

        if storage_type == "s3":
            return ""

        raise ValueError(f"Unknown storage type: {storage_type}")
