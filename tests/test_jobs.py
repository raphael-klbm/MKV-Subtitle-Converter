"""
Unit tests for controller.jobs (Jobs enum and percentage mapping).
"""
import pytest

from controller.jobs import Jobs


class TestJobsEnum:
    def test_values_are_translated_strings(self):
        # The enum values are the translation keys, but the mock returns them as-is
        assert isinstance(Jobs.IDLE.value, str)
        assert isinstance(Jobs.FINISHED.value, str)

    def test_has_expected_members(self):
        # NOTE: Jobs has a `config` class variable (not an enum member) which
        # appears in iteration. Since it's a class variable and not a proper
        # named member, we exclude it from the assertion.
        names = {j.name for j in Jobs if not j.name.startswith("config")}
        assert names == {"IDLE", "EXTRACT", "CONVERT", "REPLACE", "MUXING",
                         "FINISHED", "CANCEL"}

    def test_config_is_class_variable_not_enum(self):
        # config is set on the class (imported from config.Config), not a job state
        assert hasattr(Jobs, "config")


class TestJobsGetPercentage:
    @pytest.mark.parametrize("job, expected", [
        (Jobs.IDLE, 20),
        (Jobs.EXTRACT, 40),
        (Jobs.CONVERT, 60),
        (Jobs.MUXING, 80),
        (Jobs.FINISHED, 100),
        (Jobs.CANCEL, 0),
    ])
    def test_returns_expected_percentage(self, job, expected):
        assert Jobs.get_percentage(job) == expected

    # NOTE: REPLACE job is present in the enum but has no case in
    # get_percentage() — it will silently fall through and return None.
    # This is a latent bug: see the match statement in jobs.py.
    def test_replace_falls_through(self):
        assert Jobs.get_percentage(Jobs.REPLACE) is None