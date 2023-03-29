from ..deps.semver import SemVer


class SchemaVersion(SemVer):
    supported_versions = ('2.0', '3.0.0', '4.0.0')

    @classmethod
    def _parse(cls, ver):
        """
        Custom version string parsing to maintain backward compatibility.

        SemVer needs all of major, minor and patch parts being present in `ver`.

        :param ver:
            An integer, float or string containing a version string.

        :returns:
            List of (major, minor, patch)
        """
        try:
            if isinstance(ver, int):
                ver = float(ver)
            if isinstance(ver, float):
                ver = str(ver)
        except ValueError:
            raise ValueError('the "schema_version" is not a valid number.')

        if ver not in cls.supported_versions:
            raise ValueError(
                'the "schema_version" is not recognized. Must be one of: %s or %s.'
                % (', '.join(cls.supported_versions[:-1]), cls.supported_versions[-1])
            )

        if ver.count('.') == 1:
            ver += '.0'

        return SemVer._parse(ver)
