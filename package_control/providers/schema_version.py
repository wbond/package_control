from ..pep440 import PEP440Version


class SchemaVersion(PEP440Version):
    supported_versions = ('2.0', '3.0.0', '4.0.0')

    def __init__(self, ver):
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

        if ver not in self.supported_versions:
            raise ValueError(
                'the "schema_version" is not recognized. Must be one of: %s or %s.'
                % (', '.join(self.supported_versions[:-1]), self.supported_versions[-1])
            )

        super().__init__(ver)
