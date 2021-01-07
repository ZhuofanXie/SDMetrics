import numpy as np
import pandas as pd

def majority(samples, ignore_none = True):
    """
    Find the most frequent element in a list.

    Arguments:
        samples (list): Input list. Its elements must be hashable.
        ignore_none (bool): If None is a valid value.

    Returns:
        object: The most frequent element in samples. Returns none if the input list is empty.
    """
    freq_dict = {}
    most_freq_ele = None
    highest_freq = 0
    for element in samples:
        if ignore_none and element == None:
            continue
        if element not in freq_dict:
            freq_dict[element] = 0
        freq = freq_dict[element] + 1
        freq_dict[element] = freq
        if freq > highest_freq:
            highest_freq = freq
            most_freq_ele = element
    return most_freq_ele

def count_frequency(samples, target):
    """
    Calculate how frequent an target attribute appear in a list

    Arguments:
        samples (list): Input list. Its elements must be hashable.
        target (object): The target element.

    Returns:
        float: The frequency that target appears in samples. Must be in between 0 and 1.
    """
    count = 0
    for ele in samples:
        if ele == target:
            count += 1
    return count / len(samples)

def hamming_distance(target, test):
    """
    Calculate the hamming distance between two tuples.

    Arguments:
        target (tuple): the target tuple.
        test (tuple): the test tuple. Must have same length as target

    Returns:
        int: the hamming distance
    """
    dist = 0
    assert len(target) == len(test), "Tuples must have the same length in the \
        calculation of hamming distance!"
    for target_entry, test_entry in zip(target, test):
        if target_entry != test_entry:
            dist += 1
    return dist

def closest_neighbors(samples, target):
    """
    Find out the elements in a given list that are closest to a given
        element in hamming distance.

    Arguments:
        samples (iterable[tuple]): the given list to look up for.
        target (tuple): the target tuple.

    Returns:
        list [tuple]: elements in samples that are closest to target
    """
    dist = float("inf")
    ret = []
    for element in samples:
        hamming_dist = hamming_distance(target, element)
        if hamming_dist < dist:
            dist = hamming_dist
            ret = [element,]
        elif hamming_dist == dist:
            ret.append(element)
    return ret

def allow_nan(df):
    """
    Replace all invalid (nan and None) entries in a dataframe with valid placeholders.

    Arguments:
        df (pandas.DataFrame): the target dataframe

    Returns:
        pandas.DataFrame: a modified dataframe
    """
    df_copy = df.copy()
    for i in df_copy:
        for j in range(len(df_copy[i])):
            entry = df_copy[i][j]
            if (type(entry) == float and np.isnan(entry)) or entry == None:
                df_copy[i][j] = 'place_holder_for_nan'
    return df_copy

def allow_nan_array(attributes):
    """
    Replace all invalid (nan and None) entries in an array with valid placeholders.

    Arguments:
        attributes (tuple): the target array

    Returns:
        list: the modified array
    """
    ret = []
    for entry in attributes:
        if (type(entry) == float and np.isnan(entry)) or entry == None:
            ret.append('place_holder_for_nan')
        else:
            ret.append(entry)
    return ret