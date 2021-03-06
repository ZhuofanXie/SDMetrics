"""Base class for privacy metrics for single table datasets."""
from enum import Enum

import numpy as np

from sdmetrics.goal import Goal
from sdmetrics.single_table.base import SingleTableMetric
from sdmetrics.single_table.privacy.loss import CdfInvLp


class CategoricalType(Enum):
    """
    This enumerates the type required for a categorical data; the value
    can be one-hot-encoded, or coded as class number.
    """
    CLASS_NUM = "Class_num"
    ONE_HOT = "One_hot"


class CatPrivacyMetric(SingleTableMetric):
    """Base class for Categorical Privacy metrics on single tables.

    These metrics fit a adversial attacker model on the synthetic data and
    then evaluate its accuracy (or probability of making the correct attack)
    on the real data.

    Attributes:
        name (str):
            Name to use when reports about this metric are printed.
        goal (sdmetrics.goal.Goal):
            The goal of this metric.
        min_value (Union[float, tuple[float]]):
            Minimum value or values that this metric can take.
        max_value (Union[float, tuple[float]]):
            Maximum value or values that this metric can take.
        model:
            Model class to use for the prediction.
        model_kwargs:
            Keyword arguments to use to create the model instance.
        accuracy_base (bool):
            True if the privacy score should be based on the accuracy of the attacker,
            False if it should be based on the probability of making the correct attack.
    """

    name = None
    goal = Goal.MINIMIZE
    min_value = 0
    max_value = 1
    MODEL = None
    MODEL_KWARGS = {}
    ACCURACY_BASE = None

    @classmethod
    def _fit(cls, synthetic_data, key, sensitive, model_kwargs):
        if model_kwargs is None:
            model_kwargs = cls.MODEL_KWARGS.copy() if cls.MODEL_KWARGS else {}
        model = cls.MODEL(**model_kwargs)
        model.fit(synthetic_data, key, sensitive)
        return model

    @classmethod
    def _validate_inputs(cls, real_data, synthetic_data, metadata, key, sensitive):
        metadata = super()._validate_inputs(real_data, synthetic_data, metadata)
        if 'key' in metadata:
            key = metadata['key']
        elif key is None:
            raise TypeError('`key` must be passed either directly or inside `metadata`')

        if 'sensitive' in metadata:
            sensitive = metadata['sensitive']
        elif sensitive is None:
            raise TypeError('`sensitive` must be passed either directly or inside `metadata`')

        return key, sensitive, metadata

    @classmethod
    def compute(cls, real_data, synthetic_data, metadata=None, key=[], sensitive=[],
                model_kwargs=None):
        """Compute this metric.

        This fits a adversial attacker model on the synthetic data and
        then evaluates it making predictions on the real data.

        A ``key`` column(s) name must be given, either directly or as a first level
        entry in the ``metadata`` dict, which will be used as the key column(s) for the
        attack.

        A ``sensitive`` column(s) name must be given, either directly or as a first level
        entry in the ``metadata`` dict, which will be used as the sensitive column(s) for the
        attack.

        Args:
            real_data (Union[numpy.ndarray, pandas.DataFrame]):
                The values from the real dataset.
            synthetic_data (Union[numpy.ndarray, pandas.DataFrame]):
                The values from the synthetic dataset.
            metadata (dict):
                Table metadata dict. If not passed, it is build based on the
                real_data fields and dtypes.
            key (list(str)):
                Name of the column(s) to use as the key attributes.
            sensitive (list(str)):
                Name of the column(s) to use as the sensitive attributes.
            model_kwargs (dict):
                Key word arguments of the attacker model. cls.MODEL_KWARGS will be used
                if noen is provided.

        Returns:
            union[float, tuple[float]]:
                Scores obtained by the attackers when evaluated on the real data.
        """
        key, sensitive, metadata = cls._validate_inputs(real_data, synthetic_data,
                                                        metadata, key, sensitive)

        if len(key) == 0 or len(sensitive) == 0:  # empty key or sensitive
            return np.nan

        for col in key + sensitive:
            data_type = metadata['fields'][col]
            if data_type != cls._DTYPES_TO_TYPES['i'] and data_type != cls._DTYPES_TO_TYPES['O']\
                    and data_type != cls._DTYPES_TO_TYPES['b']:  # check data type
                return np.nan

        model = cls._fit(synthetic_data, key, sensitive, model_kwargs)

        if cls.ACCURACY_BASE:  # calculate privacy score based on prediction accuracy
            count = len(real_data)
            match = 0
            for idx in range(count):
                key_data = tuple(real_data[key].iloc[idx])
                sensitive_data = tuple(real_data[sensitive].iloc[idx])
                pred_sensitive = model.predict(key_data)
                if pred_sensitive == sensitive_data:
                    match += 1
            return match / count
        else:  # calculate privacy score based on posterior prob of the correct sensitive data
            count = 0
            score = 0
            for idx in range(len(real_data)):
                key_data = tuple(real_data[key].iloc[idx])
                sensitive_data = tuple(real_data[sensitive].iloc[idx])
                row_score = model.score(key_data, sensitive_data)
                if row_score is not None:
                    count += 1
                    score += row_score
            if count == 0:
                return 0
            return score / count


class NumPrivacyMetric(SingleTableMetric):
    """Base class for Numerical Privacy metrics on single tables.

    These metrics fit a adversial attacker model on the synthetic data and
    then evaluate its accuracy (or probability of making the correct attack)
    on the real data.

    Attributes:
        name (str):
            Name to use when reports about this metric are printed.
        goal (sdmetrics.goal.Goal):
            The goal of this metric.
        min_value (Union[float, tuple[float]]):
            Minimum value or values that this metric can take.
        max_value (Union[float, tuple[float]]):
            Maximum value or values that this metric can take.
        model (Class):
            Model class to use for the prediction.
        model_kwargs (dict):
            Keyword arguments to use to create the model instance.
        loss_function (Class):
            Loss function to use when evaluating the accuracy of the privacy attack.
        loss_function_kwargs (dict):
            Keyword arguments to use to create the loss function instance.
    """

    name = None
    goal = Goal.MAXIMIZE
    min_value = 0
    max_value = np.inf
    MODEL = None
    MODEL_KWARGS = {}
    LOSS_FUNCTION = CdfInvLp
    LOSS_FUNCTION_KWARGS = {'p': 2}

    @classmethod
    def _fit(cls, synthetic_data, key, sensitive, model_kwargs):
        if model_kwargs is None:
            model_kwargs = cls.MODEL_KWARGS.copy() if cls.MODEL_KWARGS else {}
        model = cls.MODEL(**model_kwargs)
        model.fit(synthetic_data, key, sensitive)
        return model

    @classmethod
    def _validate_inputs(cls, real_data, synthetic_data, metadata, key, sensitive):
        metadata = super()._validate_inputs(real_data, synthetic_data, metadata)
        if 'key' in metadata:
            key = metadata['key']
        elif key is None:
            raise TypeError('`key` must be passed either directly or inside `metadata`')

        if 'sensitive' in metadata:
            sensitive = metadata['sensitive']
        elif sensitive is None:
            raise TypeError('`sensitive` must be passed either directly or inside `metadata`')

        return key, sensitive, metadata

    @classmethod
    def compute(cls, real_data, synthetic_data, metadata=None, key=[], sensitive=[],
                model_kwargs=None, loss_func=None, loss_function_kwargs=None):
        """Compute this metric.

        This fits a adversial attacker model on the synthetic data and
        then evaluates it making predictions on the real data.

        A ``key`` column(s) name must be given, either directly or as a first level
        entry in the ``metadata`` dict, which will be used as the key column(s) for the
        attack.

        A ``sensitive`` column(s) name must be given, either directly or as a first level
        entry in the ``metadata`` dict, which will be used as the sensitive column(s) for the
        attack.

        Args:
            real_data (Union[numpy.ndarray, pandas.DataFrame]):
                The values from the real dataset.
            synthetic_data (Union[numpy.ndarray, pandas.DataFrame]):
                The values from the synthetic dataset.
            metadata (dict):
                Table metadata dict. If not passed, it is build based on the
                real_data fields and dtypes.
            key (list(str)):
                Name of the column(s) to use as the key attributes.
            sensitive (list(str)):
                Name of the column(s) to use as the sensitive attributes.
            model_kwargs (dict):
                Key word arguments of the attacker model. cls.MODEL_KWARGS will be used
                if none is provided.
            loss_func (Class):
                The loss function to use. cls.LOSS_FUNC will be used if none is provided.
            loss_function_kwargs (dict):
                Key word arguments of the loss function. cls.LOSS_FUNCTION_KWARGS will be used
                if none is provided.

        Returns:
            union[float, tuple[float]]:
                Scores obtained by the attackers when evaluated on the real data.
        """
        key, sensitive, metadata = cls._validate_inputs(real_data, synthetic_data,
                                                        metadata, key, sensitive)

        if len(key) == 0 or len(sensitive) == 0:  # empty key or sensitive
            return np.nan

        for col in key + sensitive:
            data_type = metadata['fields'][col]
            if data_type != cls._DTYPES_TO_TYPES['i'] and data_type != cls._DTYPES_TO_TYPES['f']:
                # check data type
                return np.nan

        model = cls._fit(synthetic_data, key, sensitive, model_kwargs)

        if loss_function_kwargs is None:
            loss_function_kwargs = cls.LOSS_FUNCTION_KWARGS

        if loss_func is None:
            loss_func = cls.LOSS_FUNCTION(**loss_function_kwargs)
        else:
            loss_func = loss_func(**loss_function_kwargs)

        loss_func.fit(real_data, sensitive)

        count = len(real_data)
        score = 0
        for idx in range(count):
            key_data = tuple(real_data[key].iloc[idx])
            sensitive_data = tuple(real_data[sensitive].iloc[idx])
            pred_sensitive = model.predict(key_data)
            score += loss_func.measure(pred_sensitive, sensitive_data)
        return score / count


class PrivacyAttackerModel():
    def fit(self, synthetic_data, key, sensitive):
        """Fit the attacker on the synthetic data.

        Args:
            synthetic_data(pandas.DataFrame):
                The synthetic data table used for adverserial learning.
            key(list[str]):
                The names of the key columns.
            semsitive(list[str]):
                The names of the sensitive columns.
        """
        raise NotImplementedError("Please implement fit method of attackers")

    def predict(self, key_data):
        """Make a prediction of the sensitive data given keys.

        Args:
            key_data(tuple):
                The key data.

        Returns:
            tuple:
                The predicted sensitive data.
        """
        raise NotImplementedError("Please implement predict method of attackers")

    def score(self, key_data, sensitive_data):
        """Score based on the belief of the attacker, in the form P(sensitive_data|key|data)

        Args:
            key_data(tuple):
                The key data.
            sensitive_data(tuple):
                The sensitive data.
        """
        raise NotImplementedError("Posterior probability based scoring not supported\
            for this attacker!")
