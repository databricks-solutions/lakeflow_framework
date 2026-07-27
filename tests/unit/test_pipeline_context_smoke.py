"""Smoke test: pipeline_context fixture bootstraps pipeline_config singletons."""


def test_pipeline_context_provides_logger(pipeline_context):
    import lakeflow_framework.pipeline_config as pipeline_config

    assert pipeline_config.get_logger() is pipeline_context["logger"]


def test_pipeline_context_provides_spark_and_dbutils(pipeline_context):
    import lakeflow_framework.pipeline_config as pipeline_config

    assert pipeline_config.get_spark() is pipeline_context["spark"]
    assert pipeline_config.get_dbutils() is pipeline_context["dbutils"]


def test_pipeline_context_substitution_manager_is_initialized(pipeline_context):
    import lakeflow_framework.pipeline_config as pipeline_config

    mgr = pipeline_config.get_substitution_manager()
    assert mgr.substitute_string("plain") == "plain"
