# -*- coding: utf-8 -*-

"""Top-level package for SDMetrics."""

__author__ = 'MIT Data To AI Lab'
__email__ = 'dailabmit@gmail.com'
__version__ = '0.1.0.dev0'

from enum import Enum

import pandas as pd


def _validate(metadata, real, synthetic):
    """
    This checks to make sure the real and synthetic databases correspond to
    the given metadata object.
    """
    metadata.validate(real)
    metadata.validate(synthetic)


def _metrics(metadata, real, synthetic):
    """
    This function takes in (1) a `sdv.Metadata` object which describes a set of
    relational tables, (2) a set of "real" tables corresponding to the metadata,
    and (3) a set of "synthetic" tables corresponding to the metadata. It yields
    a sequence of `Metric` objects.

    Args:
        metadata (sdv.Metadata): The Metadata object from SDV.
        real_tables (dict): A dictionary mapping table names to dataframes.
        synthetic_tables (dict): A dictionary mapping table names to dataframes.

    Yields:
        Metric: The next metric.
    """
    from . import constraint, detection, statistical
    _validate(metadata, real, synthetic)
    yield from constraint.metrics(metadata, real, synthetic)
    yield from detection.metrics(metadata, real, synthetic)
    yield from statistical.metrics(metadata, real, synthetic)


def evaluate(metadata, real, synthetic):
    """
    This generates a MetricsReport for the given metadata and tables with the
    default/built-in metrics.

    Args:
        metadata (sdv.Metadata): The Metadata object from SDV.
        real_tables (dict): A dictionary mapping table names to dataframes.
        synthetic_tables (dict): A dictionary mapping table names to dataframes.

    Returns:
        MetricsReport: A report containing the default metrics.
    """
    _validate(metadata, real, synthetic)
    report = MetricsReport()
    report.add_metrics(_metrics(metadata, real, synthetic))
    return report


class Goal(Enum):
    """
    This enumerates the `goal` for a metric; the value of a metric can be ignored,
    minimized, or maximized.
    """

    IGNORE = "ignore"
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class Metric():
    """
    This represents a single instance of a Metric.

    Attributes:
        name (str): The name of the attribute.
        value (float): The value of the attribute.
        tags (set(str)): A set of arbitrary strings/tags for the attribute.
        goal (Goal): Whether the value should maximized, minimized, or ignored.
        unit (str): The "unit" of the metric (i.e. p-value, entropy, mean-squared-error).
        domain (tuple): The range of values the metric can take on.
        description (str): An arbitrary text description of the attribute.
    """

    def __init__(self, name, value, tags=None, goal=Goal.IGNORE,
                 unit="", domain=(float("-inf"), float("inf")), description=""):
        self.name = name
        self.value = value
        self.tags = tags if tags else set()
        self.goal = goal
        self.unit = unit
        self.domain = domain
        self.description = description
        self._validate()

    def _validate(self):
        assert isinstance(self.name, str)
        assert isinstance(self.value, float)
        assert isinstance(self.tags, set)
        assert isinstance(self.goal, Goal)
        assert isinstance(self.unit, str)
        assert isinstance(self.domain, tuple)
        assert isinstance(self.description, str)
        assert self.domain[0] <= self.value and self.value <= self.domain[1]
        assert all(isinstance(t, str) for t in self.tags)

    def __eq__(self, other):
        my_attrs = (self.name, self.value, self.goal, self.unit)
        your_attrs = (other.name, other.value, other.objective, self.unit)
        return my_attrs == your_attrs

    def __hash__(self):
        return hash(self.name) + hash(self.value)

    def __str__(self):
        return """Metric(\n  name=%s, \n  value=%.2f, \n  tags=%s, \n  description=%s\n)""" % (
            self.name, self.value, self.tags, self.description)


class MetricsReport():
    """
    The `MetricsReport` object is responsible for storing metrics and providing a user
    friendly API for accessing them.
    """

    def __init__(self):
        self.metrics = []

    def add_metric(self, metric):
        """
        This adds the given `Metric` object to this report.
        """
        assert isinstance(metric, Metric)
        self.metrics.append(metric)

    def add_metrics(self, iterator):
        """
        This takes an iterator which yields `Metric` objects and adds all
        of these metrics to this report.
        """
        for metric in iterator:
            self.add_metric(metric)

    def overall(self):
        """
        This computes a single scalar score for this report. To produce higher quality
        synthetic data, the model should try to maximize this score.

        Returns:
            float: The scalar value to maximize.
        """
        score = 0.0
        for metric in self.metrics:
            if metric.goal == Goal.MAXIMIZE:
                score += metric.value
            elif metric.goal == Goal.MINIMIZE:
                score -= metric.value
        return score

    def details(self, filter_func=None):
        """
        This returns a DataFrame containing all of the metrics in this report. You can
        optionally use `filter_func` to specify a lambda function which takes in the
        metric and returns True if it should be included in the output.

        Args:
            filter_func (function, optional): A function which takes a Metric object
                and returns True if it should be included. Defaults to accepting all
                Metric objects.

        Returns:
            DataFrame: A table listing all the (selected) metrics.
        """
        if not filter_func:
            def filter_func(metric):
                return True
        rows = []
        for metric in self.metrics:
            if not filter_func(metric):
                continue
            table_tags = [tag for tag in metric.tags if "table:" in tag]
            column_tags = [tag for tag in metric.tags if "column:" in tag]
            misc_tags = metric.tags - set(table_tags) - set(column_tags)
            rows.append({
                "Name": metric.name,
                "Value": metric.value,
                "Goal": metric.goal,
                "Unit": metric.unit,
                "Tables": ",".join(table_tags),
                "Columns": ",".join(column_tags),
                "Misc. Tags": ",".join(misc_tags),
            })
        return pd.DataFrame(rows)

    def highlights(self):
        """
        This returns a DataFrame containing all of the metrics in this report which
        contain the "priority:high" tag.

        Returns:
            DataFrame: A table listing all the high-priority metrics.
        """
        return self.details(lambda metric: "priority:high" in metric.tags)

    def visualize(self):
        """
        This returns a pyplot.Figure which shows some of the key metrics in this report.

        Returns:
            pyplot.Figure: A matplotlib figure visualizing key metricss.
        """
        import seaborn as sns
        import matplotlib.pyplot as plt

        fig = plt.figure(figsize=(16, 9), constrained_layout=True)
        gs = fig.add_gridspec(4, 3)

        fig.add_subplot(gs[:2, :])
        labels, scores = [], []
        for metric in self.metrics:
            if metric.name == "logistic":
                tables = [tag.replace("table:", "")
                          for tag in metric.tags if "table:" in tag]
                labels.append(" <-> ".join(tables))
                scores.append(metric.value)
        df = pd.DataFrame({"score": scores, "label": labels}
                          ).sort_values("score", ascending=False)
        sns.barplot(
            x="score",
            y="label",
            data=df,
            orient="h",
            palette=sns.color_palette(
                "RdYlGn",
                10))
        plt.axvline(0.9, color="red", linestyle=":", label="Easy To Detect")
        plt.axvline(0.75, color="green", linestyle=":", label="Hard To Detect")
        plt.legend(loc="lower right")
        plt.title("Adversarial Detectability")
        plt.xlabel("AUROC (Smaller is Better)")
        plt.ylabel("")

        fig.add_subplot(gs[2:, :2])
        labels, scores = [], []
        for metric in self.metrics:
            if metric.name == "chisquare":
                table = [tag.replace("table:", "")
                         for tag in metric.tags if "table:" in tag][0]
                column = [tag.replace("column:", "")
                          for tag in metric.tags if "column:" in tag][0]
                labels.append("%s.%s" % (table, column))
                scores.append(metric.value)
        df = pd.DataFrame({"score": scores, "label": labels}
                          ).sort_values("score", ascending=True)
        sns.barplot(
            x="score",
            y="label",
            data=df,
            orient="h",
            palette=sns.color_palette(
                "RdYlGn",
                10))
        plt.title("Categorical Columns")
        plt.xlabel("Chi Squared Test (Bigger is Better)")
        plt.ylabel("")

        fig.add_subplot(gs[2:, 2:])
        labels, scores = [], []
        for metric in self.metrics:
            if metric.name == "kstest":
                table = [tag.replace("table:", "")
                         for tag in metric.tags if "table:" in tag][0]
                column = [tag.replace("column:", "")
                          for tag in metric.tags if "column:" in tag][0]
                labels.append("%s.%s" % (table, column))
                scores.append(metric.value)
        df = pd.DataFrame({"score": scores, "label": labels}
                          ).sort_values("score", ascending=True)
        sns.barplot(
            x="score",
            y="label",
            data=df,
            orient="h",
            palette=sns.color_palette(
                "RdYlGn",
                10))
        plt.title("Continuous Columns")
        plt.xlabel("KS Test (Bigger is Better)")
        plt.ylabel("")

        return fig
