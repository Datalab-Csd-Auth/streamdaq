from enum import auto

from scipy.stats import kendalltau, pearsonr, spearmanr
from scipy.stats.contingency import association
from strenum import LowercaseStrEnum


class CorrelationMethod(LowercaseStrEnum):
    PEARSON = auto()
    SPEARMAN = auto()
    KENDALL = auto()
    CRAMER = auto()


correlation_method_to_function_map = {
    CorrelationMethod.PEARSON: (lambda x, y: pearsonr(x, y).statistic),
    CorrelationMethod.SPEARMAN: (lambda x, y: spearmanr(x, y).statistic),
    CorrelationMethod.KENDALL: (lambda x, y: kendalltau(x, y).statistic),
    CorrelationMethod.CRAMER: (lambda x, y: association(list(zip(x, y)), method="cramer")),
}
